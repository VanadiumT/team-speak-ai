package com.example.teamspeak.bridge;

import com.example.teamspeak.config.BridgeConfig;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.github.manevolent.ts3j.event.*;
import com.github.manevolent.ts3j.protocol.packet.PacketBody0Voice;
import com.github.manevolent.ts3j.protocol.packet.PacketBody1VoiceWhisper;
import com.github.manevolent.ts3j.protocol.socket.client.LocalTeamspeakClientSocket;
import jakarta.websocket.*;
import jakarta.websocket.server.ServerEndpointConfig;
import org.apache.catalina.Context;
import org.apache.catalina.LifecycleException;
import org.apache.catalina.startup.Tomcat;
import org.apache.catalina.Wrapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.net.InetSocketAddress;
import java.util.Base64;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.AtomicReference;

public class TeamSpeakVoiceBridge implements TS3Listener {

    private static final Logger log = LoggerFactory.getLogger(TeamSpeakVoiceBridge.class);

    private final BridgeConfig config;
    private final ObjectMapper objectMapper;

    private volatile LocalTeamspeakClientSocket ts3Client;
    private final WebSocketAudioSource audioSource;
    private final BlockingQueue<VoiceMessage> sendQueue;
    private final AtomicInteger sequence = new AtomicInteger(0);
    private final ScheduledExecutorService scheduler;
    private final AtomicReference<Session> wsSession = new AtomicReference<>();
    private Tomcat tomcat;
    private volatile boolean running = false;
    private final ConcurrentHashMap<Integer, String> clientNames = new ConcurrentHashMap<>();
    private final Semaphore wsSendLock = new Semaphore(1);
    private final AtomicLong droppedVoiceCount = new AtomicLong(0);

    public TeamSpeakVoiceBridge(BridgeConfig config) {
        this.config = config;
        this.objectMapper = new ObjectMapper();
        this.audioSource = new WebSocketAudioSource(config.getMicrophoneQueueCapacity());
        this.sendQueue = new LinkedBlockingQueue<>(config.getVoiceQueueCapacity());
        this.scheduler = Executors.newScheduledThreadPool(config.getSchedulerPoolSize(), r -> {
            Thread t = new Thread(r, "VoiceBridge-Scheduler");
            t.setDaemon(true);
            return t;
        });
    }

    public void start() throws Exception {
        if (running) {
            log.warn("桥接服务已在运行");
            return;
        }

        log.info("启动 TeamSpeak 语音桥接服务...");

        initTs3Client();
        startWebSocketServer();
        startScheduledTasks();

        running = true;
        log.info("TeamSpeak 语音桥接服务已启动");
        log.info("  - WebSocket: ws://localhost:{}{}", config.getWsPort(), config.getWsPath());
        log.info("  - TeamSpeak: {}:{}", config.getTsHost(), config.getTsPort());
    }

    public void stop() {
        if (!running) return;

        log.info("停止 TeamSpeak 语音桥接服务...");
        running = false;
        scheduler.shutdownNow();

        if (tomcat != null) {
            try {
                tomcat.stop();
                tomcat.destroy();
            } catch (LifecycleException e) {
                log.error("停止 Tomcat 失败", e);
            }
        }

        if (ts3Client != null) {
            try {
                ts3Client.disconnect();
            } catch (Exception e) {
                log.error("断开 TeamSpeak 连接失败", e);
            }
        }

        log.info("TeamSpeak 语音桥接服务已停止");
    }

    private void initTs3Client() throws Exception {
        ts3Client = new LocalTeamspeakClientSocket();
        ts3Client.setIdentity(com.github.manevolent.ts3j.identity.LocalIdentity.generateNew(config.getIdentityDifficulty()));
        ts3Client.setNickname(config.getTsNickname());
        audioSource.setCodec(config.getDefaultCodec());
        ts3Client.setMicrophone(audioSource);
        ts3Client.setVoiceHandler(this::onReceivedVoice);
        ts3Client.setWhisperHandler(this::onReceivedWhisper);
        ts3Client.addListener(this);
        log.debug("TeamSpeak 客户端初始化完成");
    }

    private void startWebSocketServer() throws Exception {
        tomcat = new Tomcat();
        tomcat.setPort(config.getWsPort());
        tomcat.getConnector();

        // addContext 创建最小上下文，不加载默认 web.xml（避免 JSP servlet 注册）
        Context context = tomcat.addContext("", System.getProperty("java.io.tmpdir"));

        // 禁用 JAR 扫描，防止尝试加载 Jasper (JSP)
        context.getJarScanner().setJarScanFilter((jarScanType, attributes) -> false);

        // 手动初始化 WebSocket 支持（WsSci 实现 ServletContainerInitializer）
        try {
            new org.apache.tomcat.websocket.server.WsSci().onStartup(null, context.getServletContext());
        } catch (Exception e) {
            log.warn("WsSci.onStartup 跳过: {}", e.getMessage());
        }

        // 手动注册 WebSocket 端点（JAR 扫描已禁用，@ServerEndpoint 注解不会被自动发现）
        ServerEndpointConfig sec = ServerEndpointConfig.Builder
                .create(VoiceWebSocketEndpoint.class, config.getWsPath())
                .build();
        context.getServletContext().addEndpoint(sec);

        VoiceWebSocketEndpoint.registerBridge(config.getWsPath(), this);

        tomcat.start();
        log.debug("WebSocket 服务器已启动，端口: {}", config.getWsPort());
    }

    private void startScheduledTasks() {
        scheduler.scheduleAtFixedRate(this::dispatchVoiceQueue, 0, config.getDispatchIntervalMs(), TimeUnit.MILLISECONDS);
        scheduler.scheduleAtFixedRate(this::sendHeartbeat, config.getHeartbeatIntervalSeconds(),
                config.getHeartbeatIntervalSeconds(), TimeUnit.SECONDS);
    }

    private void enqueueVoiceMessage(VoiceMessageType type, int clientId,
                                      String codecType, byte[] codecData) {
        if (codecData == null || codecData.length == 0) return;
        VoiceMessage msg = new VoiceMessage();
        msg.setType(type);
        msg.setSenderId(clientId);
        msg.setSenderName(clientNames.get(clientId));
        msg.setCodecType(codecType);
        msg.setData(Base64.getEncoder().encodeToString(codecData));
        msg.setTimestamp(System.currentTimeMillis());
        msg.setSequence(sequence.incrementAndGet());
        if (!sendQueue.offer(msg)) {
            long dropped = droppedVoiceCount.incrementAndGet();
            log.warn("语音消息丢弃 (累计 {}), 队列已满: {}/{}",
                     dropped, sendQueue.size(), config.getVoiceQueueCapacity());
        }
    }

    private void onReceivedVoice(PacketBody0Voice voice) {
        if (voice == null) return;
        enqueueVoiceMessage(VoiceMessageType.VOICE, voice.getClientId(),
                            voice.getCodecType().name(), voice.getCodecData());
    }

    private void onReceivedWhisper(PacketBody1VoiceWhisper whisper) {
        if (whisper == null) return;
        enqueueVoiceMessage(VoiceMessageType.WHISPER, whisper.getClientId(),
                            whisper.getCodecType().name(), whisper.getCodecData());
    }

    // Max messages to dispatch per tick (configurable, default 20)

    private void dispatchVoiceQueue() {
        if (!wsSendLock.tryAcquire()) return;

        Session session = wsSession.get();
        if (session == null || !session.isOpen()) {
            wsSendLock.release();
            return;
        }

        try {
            int dispatched = 0;
            while (dispatched < config.getMaxDispatchPerTick()) {
                VoiceMessage msg = sendQueue.poll();
                if (msg == null) break;
                if (!session.isOpen()) {
                    sendQueue.clear();
                    break;
                }
                try {
                    String json = objectMapper.writeValueAsString(msg);
                    session.getBasicRemote().sendText(json);
                    dispatched++;
                } catch (Exception e) {
                    log.error("发送 WebSocket 消息失败, 尝试放回队列", e);
                    if (!sendQueue.offer(msg)) {
                        log.error("放回队列失败, 消息永久丢失: seq={}", msg.getSequence());
                    }
                    if (!session.isOpen()) {
                        sendQueue.clear();
                        break;
                    }
                }
            }
            if (!sendQueue.isEmpty()) {
                log.debug("语音队列仍有 {} 条待发送", sendQueue.size());
            }
        } finally {
            wsSendLock.release();
        }
    }

    private void sendHeartbeat() {
        if (!wsSendLock.tryAcquire()) return;

        Session session = wsSession.get();
        if (session != null && session.isOpen()) {
            try {
                VoiceMessage heartbeat = new VoiceMessage(VoiceMessageType.HEARTBEAT);
                heartbeat.setTimestamp(System.currentTimeMillis());
                session.getBasicRemote().sendText(objectMapper.writeValueAsString(heartbeat));
            } catch (Exception e) {
                log.warn("心跳发送失败", e);
            } finally {
                wsSendLock.release();
            }
        } else {
            wsSendLock.release();
        }
    }

    public void onWsOpen(Session session) {
        wsSession.set(session);
        audioSource.setReady(true);
        log.info("WebSocket 连接已建立: {}", session.getId());

        if (!wsSendLock.tryAcquire()) return;
        try {
            VoiceMessage connected = new VoiceMessage(VoiceMessageType.CONTROL);
            connected.setData("connected");
            connected.setTimestamp(System.currentTimeMillis());
            session.getBasicRemote().sendText(objectMapper.writeValueAsString(connected));
        } catch (Exception e) {
            log.warn("发送连接通知失败", e);
        } finally {
            wsSendLock.release();
        }
    }

    public void onWsMessage(String text, Session session) {
        try {
            VoiceMessage msg = objectMapper.readValue(text, VoiceMessage.class);
            handleMessage(msg);
        } catch (Exception e) {
            log.error("解析 WebSocket 消息失败: {}", text, e);
        }
    }

    private void handleMessage(VoiceMessage msg) {
        if (msg == null || msg.getType() == null) return;

        switch (msg.getType()) {
            case SEND_VOICE:
                handleSendVoice(msg);
                break;
            case CONTROL:
                handleControl(msg.getAction());
                break;
            case HEARTBEAT:
                log.debug("收到心跳响应");
                break;
            default:
                log.debug("收到未知类型消息: {}", msg.getType());
        }
    }

    private void handleSendVoice(VoiceMessage msg) {
        if (msg.getData() == null) return;
        try {
            byte[] audioData = Base64.getDecoder().decode(msg.getData());
            audioSource.offerAudio(audioData);
        } catch (Exception e) {
            log.error("处理音频数据失败", e);
        }
    }

    private void handleControl(String action) {
        if (action == null) return;
        switch (action.toLowerCase()) {
            case "mute":
                audioSource.setMuted(true);
                log.info("麦克风已静音");
                break;
            case "unmute":
                audioSource.setMuted(false);
                audioSource.setReady(true);
                log.info("麦克风已取消静音");
                break;
            case "connect":
                reconnectTs3();
                break;
            case "disconnect":
                disconnectTs3();
                break;
            default:
                log.debug("收到未知控制命令: {}", action);
        }
    }

    public void onWsClose(Session session) {
        wsSession.compareAndSet(session, null);
        audioSource.setReady(false);
        log.info("WebSocket 连接已关闭: {}", session.getId());
    }

    @Override
    public void onConnected(ConnectedEvent e) {
        log.info("已连接到 TeamSpeak 服务器");
    }

    @Override
    public void onDisconnected(DisconnectedEvent e) {
        log.warn("已断开 TeamSpeak 服务器");
        scheduler.schedule(this::reconnectTs3, config.getReconnectDelaySeconds(), TimeUnit.SECONDS);
    }

    @Override
    public void onClientJoin(ClientJoinEvent e) {
        clientNames.put(e.getClientId(), e.getClientNickname());
        log.debug("客户端加入: {} ({})", e.getClientNickname(), e.getClientId());
    }

    @Override
    public void onClientLeave(ClientLeaveEvent e) {
        clientNames.remove(e.getClientId());
        log.debug("客户端离开: {}", e.getClientId());
    }

    @Override
    public void onTextMessage(TextMessageEvent e) {}

    @Override
    public void onServerEdit(ServerEditedEvent e) {}

    @Override
    public void onChannelEdit(ChannelEditedEvent e) {}

    @Override
    public void onChannelDescriptionChanged(ChannelDescriptionEditedEvent e) {}

    @Override
    public void onClientMoved(ClientMovedEvent e) {}

    @Override
    public void onChannelCreate(ChannelCreateEvent e) {}

    @Override
    public void onChannelDeleted(ChannelDeletedEvent e) {}

    @Override
    public void onChannelMoved(ChannelMovedEvent e) {}

    @Override
    public void onChannelPasswordChanged(ChannelPasswordChangedEvent e) {}

    @Override
    public void onChannelList(ChannelListEvent e) {}

    @Override
    public void onPrivilegeKeyUsed(PrivilegeKeyUsedEvent e) {}

    @Override
    public void onChannelGroupList(ChannelGroupListEvent e) {}

    @Override
    public void onServerGroupList(ServerGroupListEvent e) {}

    @Override
    public void onClientNeededPermissions(ClientNeededPermissionsEvent e) {}

    @Override
    public void onClientChannelGroupChanged(ClientChannelGroupChangedEvent e) {}

    @Override
    public void onClientChanged(ClientUpdatedEvent e) {}

    @Override
    public void onChannelSubscribed(ChannelSubscribedEvent e) {}

    @Override
    public void onChannelUnsubscribed(ChannelUnsubscribedEvent e) {}

    @Override
    public void onServerGroupClientAdded(ServerGroupClientAddedEvent e) {}

    @Override
    public void onServerGroupClientDeleted(ServerGroupClientDeletedEvent e) {}

    @Override
    public void onClientPoke(ClientPokeEvent e) {}

    @Override
    public void onClientComposing(ClientChatComposingEvent e) {}

    @Override
    public void onPermissionList(PermissionListEvent e) {}

    @Override
    public void onClientChatClosed(ClientChatClosedEvent e) {}

    @Override
    public void onClientPermHints(ClientPermHintsEvent e) {}

    @Override
    public void onChannelPermHints(ChannelPermHintsEvent e) {}

    @Override
    public void onUnknownEvent(UnknownTeamspeakEvent e) {}

    private void reconnectTs3() {
        if (!running) return;
        try {
            log.info("尝试重新连接 TeamSpeak 服务器...");
            if (ts3Client != null && !ts3Client.isConnected()) {
                InetSocketAddress address = new InetSocketAddress(config.getTsHost(), config.getTsPort());
                ts3Client.connect(address, config.getTsPassword(), config.getConnectionTimeoutSeconds() * 1000);
                log.info("TeamSpeak 服务器重连成功");
            }
        } catch (Exception e) {
            log.error("TeamSpeak 服务器重连失败", e);
            scheduler.schedule(this::reconnectTs3, config.getReconnectMaxDelaySeconds(), TimeUnit.SECONDS);
        }
    }

    private void disconnectTs3() {
        try {
            if (ts3Client != null) {
                ts3Client.disconnect();
                log.info("已断开 TeamSpeak 服务器");
            }
        } catch (Exception e) {
            log.error("断开 TeamSpeak 连接失败", e);
        }
    }

    public void connect() throws Exception {
        if (ts3Client != null) {
            InetSocketAddress address = new InetSocketAddress(config.getTsHost(), config.getTsPort());
            ts3Client.connect(address, config.getTsPassword(), config.getConnectionTimeoutSeconds() * 1000);
        }
    }

    public boolean isRunning() {
        return running;
    }
}
