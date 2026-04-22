package com.example.teamspeak.bridge;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * 语音消息结构
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class VoiceMessage {

    /**
     * 消息类型
     */
    private VoiceMessageType type;

    /**
     * 发送者客户端ID
     */
    @JsonProperty("senderId")
    private Integer senderId;

    /**
     * 发送者昵称
     */
    @JsonProperty("senderName")
    private String senderName;

    /**
     * 编码类型（如 OPUS_VOICE）
     */
    @JsonProperty("codecType")
    private String codecType;

    /**
     * 时间戳（毫秒）
     */
    @JsonProperty("timestamp")
    private Long timestamp;

    /**
     * 序列号
     */
    @JsonProperty("sequence")
    private Integer sequence;

    /**
     * Base64 编码的音频数据
     */
    @JsonProperty("data")
    private String data;

    /**
     * 控制命令动作（用于 CONTROL 类型消息）
     */
    @JsonProperty("action")
    private String action;

    public VoiceMessage() {
    }

    public VoiceMessage(VoiceMessageType type) {
        this.type = type;
    }

    public VoiceMessageType getType() {
        return type;
    }

    public void setType(VoiceMessageType type) {
        this.type = type;
    }

    public Integer getSenderId() {
        return senderId;
    }

    public void setSenderId(Integer senderId) {
        this.senderId = senderId;
    }

    public String getSenderName() {
        return senderName;
    }

    public void setSenderName(String senderName) {
        this.senderName = senderName;
    }

    public String getCodecType() {
        return codecType;
    }

    public void setCodecType(String codecType) {
        this.codecType = codecType;
    }

    public Long getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(Long timestamp) {
        this.timestamp = timestamp;
    }

    public Integer getSequence() {
        return sequence;
    }

    public void setSequence(Integer sequence) {
        this.sequence = sequence;
    }

    public String getData() {
        return data;
    }

    public void setData(String data) {
        this.data = data;
    }

    public String getAction() {
        return action;
    }

    public void setAction(String action) {
        this.action = action;
    }

    @Override
    public String toString() {
        return "VoiceMessage{" +
                "type=" + type +
                ", senderId=" + senderId +
                ", senderName='" + senderName + '\'' +
                ", codecType='" + codecType + '\'' +
                ", timestamp=" + timestamp +
                ", sequence=" + sequence +
                ", action='" + action + '\'' +
                ", dataLength=" + (data != null ? data.length() : 0) +
                '}';
    }
}
