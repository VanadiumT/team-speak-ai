package com.example.teamspeak.config;

import com.github.manevolent.ts3j.enums.CodecType;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * BridgeConfig 默认值和 getter/setter 测试
 */
class BridgeConfigTest {

    @Test
    void testDefaultValues() {
        BridgeConfig config = new BridgeConfig();
        assertEquals("localhost", config.getTsHost());
        assertEquals("", config.getTsPassword());
        assertEquals(9987, config.getTsPort());
        assertEquals("VoiceBridge", config.getTsNickname());
        assertEquals(8080, config.getWsPort());
        assertEquals("/teamspeak/voice", config.getWsPath());
        assertEquals(CodecType.OPUS_VOICE, config.getDefaultCodec());
        assertEquals(2000, config.getVoiceQueueCapacity());
        assertEquals(100, config.getMicrophoneQueueCapacity());
        assertEquals(30, config.getHeartbeatIntervalSeconds());
        assertEquals(10, config.getConnectionTimeoutSeconds());
        assertEquals(5, config.getReconnectDelaySeconds());
        assertEquals(10, config.getReconnectMaxDelaySeconds());
        assertEquals(3, config.getSchedulerPoolSize());
        assertEquals(10, config.getDispatchIntervalMs());
        assertEquals(20, config.getMaxDispatchPerTick());
        assertEquals(22, config.getIdentityDifficulty());
    }

    @Test
    void testTsHostSetter() {
        BridgeConfig config = new BridgeConfig();
        config.setTsHost("192.168.1.100");
        assertEquals("192.168.1.100", config.getTsHost());
    }

    @Test
    void testTsPortSetter() {
        BridgeConfig config = new BridgeConfig();
        config.setTsPort(10000);
        assertEquals(10000, config.getTsPort());
    }

    @Test
    void testWsPortSetter() {
        BridgeConfig config = new BridgeConfig();
        config.setWsPort(9090);
        assertEquals(9090, config.getWsPort());
    }

    @Test
    void testWsPathSetter() {
        BridgeConfig config = new BridgeConfig();
        config.setWsPath("/custom/path");
        assertEquals("/custom/path", config.getWsPath());
    }

    @Test
    void testHeartbeatInterval() {
        BridgeConfig config = new BridgeConfig();
        config.setHeartbeatIntervalSeconds(60);
        assertEquals(60, config.getHeartbeatIntervalSeconds());
    }

    @Test
    void testConnectionTimeout() {
        BridgeConfig config = new BridgeConfig();
        config.setConnectionTimeoutSeconds(30);
        assertEquals(30, config.getConnectionTimeoutSeconds());
    }

    @Test
    void testReconnectDelay() {
        BridgeConfig config = new BridgeConfig();
        config.setReconnectDelaySeconds(15);
        assertEquals(15, config.getReconnectDelaySeconds());
    }

    @Test
    void testReconnectMaxDelay() {
        BridgeConfig config = new BridgeConfig();
        config.setReconnectMaxDelaySeconds(60);
        assertEquals(60, config.getReconnectMaxDelaySeconds());
    }

    @Test
    void testVoiceQueueCapacity() {
        BridgeConfig config = new BridgeConfig();
        config.setVoiceQueueCapacity(5000);
        assertEquals(5000, config.getVoiceQueueCapacity());
    }

    @Test
    void testMicrophoneQueueCapacity() {
        BridgeConfig config = new BridgeConfig();
        config.setMicrophoneQueueCapacity(200);
        assertEquals(200, config.getMicrophoneQueueCapacity());
    }

    @Test
    void testSchedulerPoolSize() {
        BridgeConfig config = new BridgeConfig();
        config.setSchedulerPoolSize(8);
        assertEquals(8, config.getSchedulerPoolSize());
    }

    @Test
    void testDispatchIntervalMs() {
        BridgeConfig config = new BridgeConfig();
        config.setDispatchIntervalMs(5);
        assertEquals(5, config.getDispatchIntervalMs());
    }

    @Test
    void testMaxDispatchPerTick() {
        BridgeConfig config = new BridgeConfig();
        config.setMaxDispatchPerTick(50);
        assertEquals(50, config.getMaxDispatchPerTick());
    }

    @Test
    void testIdentityDifficulty() {
        BridgeConfig config = new BridgeConfig();
        config.setIdentityDifficulty(30);
        assertEquals(30, config.getIdentityDifficulty());
    }

    @Test
    void testDefaultCodec() {
        BridgeConfig config = new BridgeConfig();
        config.setDefaultCodec(CodecType.OPUS_MUSIC);
        assertEquals(CodecType.OPUS_MUSIC, config.getDefaultCodec());
    }

    @Test
    void testTsPassword() {
        BridgeConfig config = new BridgeConfig();
        config.setTsPassword("secret123");
        assertEquals("secret123", config.getTsPassword());
    }

    @Test
    void testTsNickname() {
        BridgeConfig config = new BridgeConfig();
        config.setTsNickname("AI助手");
        assertEquals("AI助手", config.getTsNickname());
    }
}
