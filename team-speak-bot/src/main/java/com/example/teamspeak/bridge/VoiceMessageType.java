package com.example.teamspeak.bridge;

/**
 * 语音消息类型枚举
 */
public enum VoiceMessageType {
    /** 普通频道语音 */
    VOICE,

    /** 私聊/耳语语音 */
    WHISPER,

    /** 客户端发送语音到 TeamSpeak */
    SEND_VOICE,

    /** 控制命令（mute/unmute/connect/disconnect） */
    CONTROL,

    /** 心跳保活 */
    HEARTBEAT
}
