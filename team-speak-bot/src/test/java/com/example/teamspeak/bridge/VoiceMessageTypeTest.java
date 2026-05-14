package com.example.teamspeak.bridge;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * VoiceMessageType 枚举测试
 */
class VoiceMessageTypeTest {

    @Test
    void testAllValuesExist() {
        VoiceMessageType[] values = VoiceMessageType.values();
        assertEquals(5, values.length);
    }

    @Test
    void testValueOf() {
        assertEquals(VoiceMessageType.VOICE, VoiceMessageType.valueOf("VOICE"));
        assertEquals(VoiceMessageType.WHISPER, VoiceMessageType.valueOf("WHISPER"));
        assertEquals(VoiceMessageType.SEND_VOICE, VoiceMessageType.valueOf("SEND_VOICE"));
        assertEquals(VoiceMessageType.CONTROL, VoiceMessageType.valueOf("CONTROL"));
        assertEquals(VoiceMessageType.HEARTBEAT, VoiceMessageType.valueOf("HEARTBEAT"));
    }

    @Test
    void testValueOfInvalidThrows() {
        assertThrows(IllegalArgumentException.class, () -> VoiceMessageType.valueOf("INVALID"));
    }

    @Test
    void testVoiceType() {
        assertEquals("VOICE", VoiceMessageType.VOICE.name());
    }

    @Test
    void testControlType() {
        assertEquals("CONTROL", VoiceMessageType.CONTROL.name());
    }
}
