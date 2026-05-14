package com.example.teamspeak.bridge;

import jakarta.websocket.*;
import jakarta.websocket.server.ServerEndpoint;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.concurrent.ConcurrentHashMap;

@ServerEndpoint(value = "/teamspeak/voice")
public class VoiceWebSocketEndpoint extends Endpoint {
    private static final Logger log = LoggerFactory.getLogger(VoiceWebSocketEndpoint.class);
    private static final ConcurrentHashMap<String, TeamSpeakVoiceBridge> bridgeMap = new ConcurrentHashMap<>();

    public static void registerBridge(String path, TeamSpeakVoiceBridge bridge) {
        bridgeMap.put(path, bridge);
    }

    private TeamSpeakVoiceBridge getBridge(Session session) {
        if (session == null) return null;
        // Match by the request path used to open this session
        String path = session.getRequestURI().getPath();
        TeamSpeakVoiceBridge bridge = bridgeMap.get(path);
        if (bridge != null) return bridge;
        // Fallback: if only one bridge registered, return it
        if (bridgeMap.size() == 1) return bridgeMap.values().iterator().next();
        return null;
    }

    @Override
    public void onOpen(Session session, EndpointConfig config) {
        TeamSpeakVoiceBridge bridge = getBridge(session);
        if (bridge != null) {
            bridge.onWsOpen(session);
        }

        session.addMessageHandler(String.class, msg -> {
            if (bridge != null) {
                bridge.onWsMessage(msg, session);
            }
        });
    }

    @Override
    public void onClose(Session session, CloseReason closeReason) {
        TeamSpeakVoiceBridge bridge = getBridge(session);
        if (bridge != null) {
            bridge.onWsClose(session);
        }
    }

    @Override
    public void onError(Session session, Throwable thr) {
        log.error("WebSocket 错误: {}", thr.getMessage(), thr);
    }
}
