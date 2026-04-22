package com.example.teamspeak.bridge;

import com.github.manevolent.ts3j.audio.Microphone;
import com.github.manevolent.ts3j.enums.CodecType;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

/**
 * 自定义麦克风实现，通过 WebSocket 注入音频数据
 *
 * ts3j 每 20ms 调用 provide() 方法获取音频数据
 */
public class WebSocketAudioSource implements Microphone {

    private static final Logger log = LoggerFactory.getLogger(WebSocketAudioSource.class);

    /**
     * 音频数据队列
     */
    private final BlockingQueue<byte[]> audioQueue;

    /**
     * 是否静音
     */
    private final AtomicBoolean muted = new AtomicBoolean(false);

    /**
     * 是否就绪
     */
    private final AtomicBoolean ready = new AtomicBoolean(false);

    /**
     * 当前编码类型
     */
    private final AtomicReference<CodecType> codec = new AtomicReference<>(CodecType.OPUS_VOICE);

    /**
     * 队列超时时间（毫秒）
     */
    private static final long POLL_TIMEOUT_MS = 25;

    public WebSocketAudioSource(int queueCapacity) {
        this.audioQueue = new LinkedBlockingQueue<>(queueCapacity);
    }

    public WebSocketAudioSource() {
        this(100);
    }

    /**
     * 从 WebSocket 接收音频数据时调用此方法注入数据
     *
     * @param audioData 音频数据
     */
    public void offerAudio(byte[] audioData) {
        if (audioData == null || audioData.length == 0) {
            return;
        }
        if (!muted.get()) {
            audioQueue.offer(audioData);
        }
    }

    /**
     * ts3j 每 20ms 调用此方法获取音频数据
     */
    @Override
    public byte[] provide() {
        if (muted.get()) {
            return new byte[0];
        }

        byte[] data = audioQueue.poll();
        if (data == null) {
            try {
                data = audioQueue.poll(POLL_TIMEOUT_MS, TimeUnit.MILLISECONDS);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return new byte[0];
            }
        }

        return data != null ? data : new byte[0];
    }

    @Override
    public CodecType getCodec() {
        return codec.get();
    }

    @Override
    public boolean isReady() {
        return ready.get() && !muted.get();
    }

    @Override
    public boolean isMuted() {
        return muted.get();
    }

    public void setCodec(CodecType codecType) {
        this.codec.set(codecType);
    }

    public void setMuted(boolean muted) {
        this.muted.set(muted);
        if (muted) {
            audioQueue.clear();
        }
        log.debug("麦克风静音状态: {}", muted);
    }

    public void setReady(boolean ready) {
        this.ready.set(ready);
        log.debug("麦克风就绪状态: {}", ready);
    }

    public int getQueueSize() {
        return audioQueue.size();
    }

    public void clearQueue() {
        audioQueue.clear();
    }

    public int getQueueCapacity() {
        return audioQueue.remainingCapacity();
    }
}
