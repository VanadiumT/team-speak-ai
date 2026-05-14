package com.example.teamspeak.config;

import com.github.manevolent.ts3j.enums.CodecType;

/**
 * 桥接服务配置 —— Java 端权威配置源。
 *
 * 配置优先级：application.properties → BridgeConfig 默认值。
 *
 * 🔗 跨服务对齐要求（此文件中的参数与其他服务必须一致）：
 *   - wsPort + wsPath → Python config.ts_ws_url 必须指向此地址
 *   - heartbeatIntervalSeconds → Python config.ts_heartbeat_interval 必须一致
 *   - connectionTimeoutSeconds → Python ts_reconnect_interval 的参考值
 */
public class BridgeConfig {

    // ========== TeamSpeak 服务器配置 ==========

    /**
     * TeamSpeak 服务器地址
     */
    private String tsHost = "localhost";

    /**
     * TeamSpeak 服务器密码
     */
    private String tsPassword = "";

    /**
     * TeamSpeak 服务器端口
     */
    private int tsPort = 9987;

    /**
     * TeamSpeak 客户端昵称
     */
    private String tsNickname = "VoiceBridge";

    // ========== WebSocket 配置 ==========

    /**
     * WebSocket 服务端口
     */
    private int wsPort = 8080;

    /**
     * WebSocket 路径
     */
    private String wsPath = "/teamspeak/voice";

    // ========== 音频配置 ==========

    /**
     * 默认音频编码类型
     */
    private CodecType defaultCodec = CodecType.OPUS_VOICE;

    /**
     * 语音队列最大容量
     */
    private int voiceQueueCapacity = 2000;

    /**
     * 麦克风队列最大容量
     */
    private int microphoneQueueCapacity = 100;

    // ========== 心跳配置 ==========

    /**
     * 心跳间隔（秒）
     */
    private int heartbeatIntervalSeconds = 30;

    // ========== 连接配置 ==========

    /**
     * TeamSpeak 连接超时时间（秒）
     */
    private int connectionTimeoutSeconds = 10;

    /**
     * 断线重连延迟（秒）—— onDisconnected 触发后的等待时间
     */
    private int reconnectDelaySeconds = 5;

    /**
     * 重连失败后的最大重试延迟（秒）—— reconnectTs3 失败后的等待时间
     */
    private int reconnectMaxDelaySeconds = 10;

    // ========== 调度配置 ==========

    /**
     * 调度线程池大小
     */
    private int schedulerPoolSize = 3;

    /**
     * 语音队列调度间隔（毫秒）—— dispatchVoiceQueue 的执行周期
     */
    private int dispatchIntervalMs = 10;

    /**
     * 每次调度最大发送消息数 —— 防止单次调度耗时过长
     */
    private int maxDispatchPerTick = 20;

    // ========== Identity 配置 ==========

    /**
     * TeamSpeak Identity 生成难度（越大越慢但越唯一）
     */
    private int identityDifficulty = 22;

    // ========== Getters and Setters ==========

    public String getTsHost() {
        return tsHost;
    }

    public void setTsHost(String tsHost) {
        this.tsHost = tsHost;
    }

    public String getTsPassword() {
        return tsPassword;
    }

    public void setTsPassword(String tsPassword) {
        this.tsPassword = tsPassword;
    }

    public int getTsPort() {
        return tsPort;
    }

    public void setTsPort(int tsPort) {
        this.tsPort = tsPort;
    }

    public String getTsNickname() {
        return tsNickname;
    }

    public void setTsNickname(String tsNickname) {
        this.tsNickname = tsNickname;
    }

    public int getWsPort() {
        return wsPort;
    }

    public void setWsPort(int wsPort) {
        this.wsPort = wsPort;
    }

    public String getWsPath() {
        return wsPath;
    }

    public void setWsPath(String wsPath) {
        this.wsPath = wsPath;
    }

    public CodecType getDefaultCodec() {
        return defaultCodec;
    }

    public void setDefaultCodec(CodecType defaultCodec) {
        this.defaultCodec = defaultCodec;
    }

    public int getVoiceQueueCapacity() {
        return voiceQueueCapacity;
    }

    public void setVoiceQueueCapacity(int voiceQueueCapacity) {
        this.voiceQueueCapacity = voiceQueueCapacity;
    }

    public int getMicrophoneQueueCapacity() {
        return microphoneQueueCapacity;
    }

    public void setMicrophoneQueueCapacity(int microphoneQueueCapacity) {
        this.microphoneQueueCapacity = microphoneQueueCapacity;
    }

    public int getHeartbeatIntervalSeconds() {
        return heartbeatIntervalSeconds;
    }

    public void setHeartbeatIntervalSeconds(int heartbeatIntervalSeconds) {
        this.heartbeatIntervalSeconds = heartbeatIntervalSeconds;
    }

    public int getConnectionTimeoutSeconds() {
        return connectionTimeoutSeconds;
    }

    public void setConnectionTimeoutSeconds(int connectionTimeoutSeconds) {
        this.connectionTimeoutSeconds = connectionTimeoutSeconds;
    }

    public int getReconnectDelaySeconds() {
        return reconnectDelaySeconds;
    }

    public void setReconnectDelaySeconds(int reconnectDelaySeconds) {
        this.reconnectDelaySeconds = reconnectDelaySeconds;
    }

    public int getReconnectMaxDelaySeconds() {
        return reconnectMaxDelaySeconds;
    }

    public void setReconnectMaxDelaySeconds(int reconnectMaxDelaySeconds) {
        this.reconnectMaxDelaySeconds = reconnectMaxDelaySeconds;
    }

    public int getSchedulerPoolSize() {
        return schedulerPoolSize;
    }

    public void setSchedulerPoolSize(int schedulerPoolSize) {
        this.schedulerPoolSize = schedulerPoolSize;
    }

    public int getDispatchIntervalMs() {
        return dispatchIntervalMs;
    }

    public void setDispatchIntervalMs(int dispatchIntervalMs) {
        this.dispatchIntervalMs = dispatchIntervalMs;
    }

    public int getMaxDispatchPerTick() {
        return maxDispatchPerTick;
    }

    public void setMaxDispatchPerTick(int maxDispatchPerTick) {
        this.maxDispatchPerTick = maxDispatchPerTick;
    }

    public int getIdentityDifficulty() {
        return identityDifficulty;
    }

    public void setIdentityDifficulty(int identityDifficulty) {
        this.identityDifficulty = identityDifficulty;
    }
}
