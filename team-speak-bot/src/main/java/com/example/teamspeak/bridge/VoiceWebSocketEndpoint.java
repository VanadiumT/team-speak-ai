package com.example.teamspeak.bridge;

import jakarta.websocket.*;
import jakarta.websocket.server.ServerEndpoint;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.nio.ByteBuffer;
import java.util.concurrent.ConcurrentHashMap;

@ServerEndpoint(value = "/teamspeak/voice")
public class VoiceWebSocketEndpoint extends Endpoint {
    private static final Logger log = LoggerFactory.getLogger(VoiceWebSocketEndpoint.class);
    private static final ConcurrentHashMap<String, TeamSpeakVoiceBridge> bridgeMap = new ConcurrentHashMap<>();

    public static void registerBridge(String path, TeamSpeakVoiceBridge bridge) {
        bridgeMap.put(path, bridge);
    }

    public static void unregisterBridge(String path) {
        bridgeMap.remove(path);
    }

    private TeamSpeakVoiceBridge getBridge() {
        for (TeamSpeakVoiceBridge bridge : bridgeMap.values()) {
            return bridge;
        }
        return null;
    }

    @Override
    public void onOpen(Session session, EndpointConfig config) {
        TeamSpeakVoiceBridge bridge = getBridge();
        if (bridge != null) {
            bridge.onWsOpen(session);
        }

        session.addMessageHandler(String.class, msg -> {
            if (bridge != null) {
                bridge.onWsMessage(msg, session);
            }
        });

        session.addMessageHandler(ByteBuffer.class, buffer -> {
            log.debug("收到二进制消息: {} bytes", buffer.remaining());
        });
    }

    @Override
    public void onClose(Session session, CloseReason closeReason) {
        TeamSpeakVoiceBridge bridge = getBridge();
        if (bridge != null) {
            bridge.onWsClose(session);
        }
    }

    @Override
    public void onError(Session session, Throwable thr) {
        log.error("WebSocket 错误: {}", thr.getMessage(), thr);
    }
}
