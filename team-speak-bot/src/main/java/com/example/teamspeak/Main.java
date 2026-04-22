package com.example.teamspeak;

import com.example.teamspeak.bridge.TeamSpeakVoiceBridge;
import com.example.teamspeak.config.BridgeConfig;
import com.github.manevolent.ts3j.enums.CodecType;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.io.InputStream;
import java.util.Properties;

/**
 * TeamSpeak Voice Bridge 启动类
 */
public class Main {

    private static final Logger log = LoggerFactory.getLogger(Main.class);

    private static final String CONFIG_FILE = "/application.properties";

    public static void main(String[] args) {
        log.info("===========================================");
        log.info("   TeamSpeak Voice Bridge v1.0.0");
        log.info("===========================================");

        // 加载配置
        BridgeConfig config = loadConfig();
        logConfiguration(config);

        // 创建桥接服务
        TeamSpeakVoiceBridge bridge = new TeamSpeakVoiceBridge(config);

        // 添加关闭钩子
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            log.info("收到关闭信号...");
            bridge.stop();
        }));

        try {
            // 启动桥接服务
            bridge.start();

            // 连接 TeamSpeak 服务器
            bridge.connect();

            log.info("服务已启动，按 Ctrl+C 停止");

            // 保持运行
            Thread.currentThread().join();
        } catch (Exception e) {
            log.error("启动失败", e);
            System.exit(1);
        }
    }

    /**
     * 加载配置
     */
    private static BridgeConfig loadConfig() {
        BridgeConfig config = new BridgeConfig();

        try (InputStream is = Main.class.getResourceAsStream(CONFIG_FILE)) {
            if (is == null) {
                log.warn("配置文件 {} 未找到，使用默认配置", CONFIG_FILE);
                return config;
            }

            Properties props = new Properties();
            props.load(is);

            // TeamSpeak 配置
            config.setTsHost(props.getProperty("teamspeak.host", "localhost"));
            config.setTsPassword(props.getProperty("teamspeak.password", ""));
            config.setTsPort(Integer.parseInt(props.getProperty("teamspeak.port", "9987")));
            config.setTsNickname(props.getProperty("teamspeak.nickname", "VoiceBridge"));
            config.setConnectionTimeoutSeconds(Integer.parseInt(props.getProperty("teamspeak.connection-timeout-seconds", "10")));

            // WebSocket 配置
            config.setWsPort(Integer.parseInt(props.getProperty("websocket.port", "8080")));
            config.setWsPath(props.getProperty("websocket.path", "/teamspeak/voice"));

            // 音频配置
            String codecName = props.getProperty("audio.codec", "OPUS_VOICE");
            try {
                config.setDefaultCodec(CodecType.valueOf(codecName));
            } catch (IllegalArgumentException e) {
                log.warn("未知的编码类型 {}，使用默认 OPUS_VOICE", codecName);
                config.setDefaultCodec(CodecType.OPUS_VOICE);
            }
            config.setVoiceQueueCapacity(Integer.parseInt(props.getProperty("audio.voice-queue-capacity", "500")));
            config.setMicrophoneQueueCapacity(Integer.parseInt(props.getProperty("audio.microphone-queue-capacity", "100")));

            // 心跳配置
            config.setHeartbeatIntervalSeconds(Integer.parseInt(props.getProperty("heartbeat.interval-seconds", "30")));

            log.info("配置文件加载成功");

        } catch (IOException e) {
            log.error("加载配置文件失败", e);
        }

        return config;
    }

    /**
     * 打印配置
     */
    private static void logConfiguration(BridgeConfig config) {
        log.info("-------------------------------------------");
        log.info("配置信息:");
        log.info("  TeamSpeak:");
        log.info("    - Host: {}", config.getTsHost());
        log.info("    - Port: {}", config.getTsPort());
        log.info("    - Nickname: {}", config.getTsNickname());
        log.info("  WebSocket:");
        log.info("    - Port: {}", config.getWsPort());
        log.info("    - Path: {}", config.getWsPath());
        log.info("  Audio:");
        log.info("    - Codec: {}", config.getDefaultCodec());
        log.info("    - Voice Queue: {}", config.getVoiceQueueCapacity());
        log.info("    - Microphone Queue: {}", config.getMicrophoneQueueCapacity());
        log.info("  Heartbeat:");
        log.info("    - Interval: {}s", config.getHeartbeatIntervalSeconds());
        log.info("-------------------------------------------");
    }
}
