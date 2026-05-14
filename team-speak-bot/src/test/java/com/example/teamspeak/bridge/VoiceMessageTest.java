package com.example.teamspeak.bridge;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * VoiceMessage 序列化/反序列化测试
 */
class VoiceMessageTest {

    private final ObjectMapper mapper = new ObjectMapper();

    @Test
    void testDefaultConstructor() {
        VoiceMessage msg = new VoiceMessage();
        assertNull(msg.getType());
        assertNull(msg.getSenderId());
        assertNull(msg.getData());
    }

    @Test
    void testTypeConstructor() {
        VoiceMessage msg = new VoiceMessage(VoiceMessageType.VOICE);
        assertEquals(VoiceMessageType.VOICE, msg.getType());
    }

    @Test
    void testGettersSetters() {
        VoiceMessage msg = new VoiceMessage();
        msg.setType(VoiceMessageType.SEND_VOICE);
        msg.setSenderId(42);
        msg.setSenderName("Alice");
        msg.setCodecType("OPUS_VOICE");
        msg.setTimestamp(1234567890L);
        msg.setSequence(1);
        msg.setData("aGVsbG8=");
        msg.setAction("mute");

        assertEquals(VoiceMessageType.SEND_VOICE, msg.getType());
        assertEquals(42, msg.getSenderId());
        assertEquals("Alice", msg.getSenderName());
        assertEquals("OPUS_VOICE", msg.getCodecType());
        assertEquals(1234567890L, msg.getTimestamp());
        assertEquals(1, msg.getSequence());
        assertEquals("aGVsbG8=", msg.getData());
        assertEquals("mute", msg.getAction());
    }

    @Test
    void testJsonSerialization() throws Exception {
        VoiceMessage msg = new VoiceMessage(VoiceMessageType.VOICE);
        msg.setSenderId(1);
        msg.setSenderName("Bob");
        msg.setData("aGVsbG8=");

        String json = mapper.writeValueAsString(msg);
        assertNotNull(json);
        assertTrue(json.contains("\"type\":\"VOICE\""));
        assertTrue(json.contains("\"senderId\":1"));
        assertTrue(json.contains("\"senderName\":\"Bob\""));
    }

    @Test
    void testJsonDeserialization() throws Exception {
        String json = "{\"type\":\"SEND_VOICE\",\"senderId\":5,\"data\":\"dGVzdA==\"}";
        VoiceMessage msg = mapper.readValue(json, VoiceMessage.class);

        assertEquals(VoiceMessageType.SEND_VOICE, msg.getType());
        assertEquals(5, msg.getSenderId());
        assertEquals("dGVzdA==", msg.getData());
    }

    @Test
    void testNullFieldsOmittedInJson() throws Exception {
        VoiceMessage msg = new VoiceMessage(VoiceMessageType.HEARTBEAT);
        String json = mapper.writeValueAsString(msg);
        assertFalse(json.contains("senderId"));
        assertFalse(json.contains("data"));
        assertFalse(json.contains("senderName"));
    }

    @Test
    void testToStringWithData() {
        VoiceMessage msg = new VoiceMessage(VoiceMessageType.VOICE);
        msg.setSenderId(1);
        msg.setData("aGVsbG8gd29ybGQ=");
        String str = msg.toString();
        assertTrue(str.contains("VOICE"));
        assertTrue(str.contains("senderId=1"));
        assertTrue(str.contains("dataLength=16"));
    }

    @Test
    void testToStringWithNullData() {
        VoiceMessage msg = new VoiceMessage(VoiceMessageType.VOICE);
        String str = msg.toString();
        assertTrue(str.contains("dataLength=0"));
    }

    @Test
    void testAllMessageTypes() {
        for (VoiceMessageType type : VoiceMessageType.values()) {
            VoiceMessage msg = new VoiceMessage(type);
            assertEquals(type, msg.getType());
        }
    }
}
