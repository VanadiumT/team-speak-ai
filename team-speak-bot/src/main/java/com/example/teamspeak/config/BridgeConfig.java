package com.example.teamspeak.config;

import com.github.manevolent.ts3j.enums.CodecType;

/**
 * 桥接服务配置
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
}
