# 节点类型注册参考

> 当前已注册的全部节点类型详细说明。通过 `@NodeRegistry.register()` 按需扩展，数量不固定。

---

## 1. `input_image` — 上传图片

| 维度 | 内容 |
|---|---|
| 功能 | 等待用户上传图片文件，输出 base64 图片数据 |
| 类别 | Source（数据源） |
| 执行模式 | One-shot（上传一次执行一次） |
| 写 accumulated_context | 否 |

**元数据：** icon=`upload_file`, color=`secondary`

**端口：**

| 方向 | id | data_type | 可见 | 说明 |
|---|---|---|---|---|
| 出 | `img-out` | `image` | always | base64 图片 |
| 出 | `trigger-out` | `event` | always | 触发下游 |

无输入端口 — 它是数据源头。

**配置：**
- `accepted_formats`: `["png", "jpg", "webp"]` — 接受的图片格式
- `max_size_mb`: `10` — 最大文件大小

**标签页：** `detail`（详情）、`io-data`（IO数据）— 没有 config tab，没有 log tab

**Flow Mode body：**
- `pending` → 点击上传区域
- `processing` → 进度条（来自 files store）
- `completed` → 文件名 + 大小 + 重新上传按钮
- `error` → 错误提示

**Edit Mode body：**
- config tab → `accepted_formats` 复选框组 + `max_size_mb` 数字输入
- detail tab → 同 Flow Mode

---

## 2. `ocr` — OCR 识别

| 维度 | 内容 |
|---|---|
| 功能 | 接收图片，调用 OCR 引擎提取文本 |
| 类别 | Transform（转换） |
| 执行模式 | One-shot |
| 写 accumulated_context | 否 |

**元数据：** icon=`document_scanner`, color=`secondary`

**端口：**

| 方向 | id | data_type | 可见 | 说明 |
|---|---|---|---|---|
| 入 | `ocr-in` | `image` | always | 待识别图片 |
| 入 | `trigger-in` | `event` | on-demand | 手动触发 |
| 出 | `ocr-out` | `string` | always | 识别文本 |
| 出 | `done` | `event` | on-demand | 完成信号 |
| 出 | `meta-confidence` | `number` | on-demand | 平均置信度 |
| 出 | `meta-region-count` | `number` | on-demand | 识别区域数 |

**配置：**
- `engine`: `"easyocr"` — OCR 引擎（easyocr / paddleocr）
- `language`: `["zh"]` — 识别语言
- `confidence_threshold`: `0.3` — 置信度阈值

**标签页：** `config`、`detail`、`io-data`、`io-mgmt`、`log`

**Flow Mode body：**
- `pending` → "等待图片..."
- `processing` → 识别中 spinner
- `completed` → 识别结果文本预览 + 行数
- `error` → 错误信息

**Edit Mode body：**
- config tab → engine 下拉、language 输入、confidence 滑块

---

## 3. `stt_listen` — STT 持续监听

| 维度 | 内容 |
|---|---|
| 功能 | 订阅 AudioBus，持续识别语音，检测到关键词时触发下游 |
| 类别 | Listener（持久监听） |
| 执行模式 | **Listener（无限循环）** — 检测到关键词才 break |
| 写 accumulated_context | 否（下游 stt_history 负责） |

**元数据：** icon=`mic_external_on`, color=`primary`

**端口：**

| 方向 | id | data_type | 可见 | 说明 |
|---|---|---|---|---|
| 入 | `stt-in` | `audio` | always | 音频帧（实际从 AudioBus 读取，不走连线） |
| 出 | `stt-out` | `string` | always | 识别文本 |
| 出 | `meta-keyword` | `string` | on-demand | 触发的关键词 |
| 出 | `meta-confidence` | `number` | on-demand | STT 置信度 |
| 出 | `meta-history-count` | `number` | on-demand | 累积历史条数 |

**配置：**
- `engine`: `"sensevoice"` — STT 引擎
- `keywords`: `["求助", "集合", "撤退"]` — 触发关键词列表
- `sample_rate`: `16000` — 采样率

**标签页：** `config`、`detail`、`io-data`、`io-mgmt`、`log`、`fulltext`

**Flow Mode body：**
- `listening` → 实时识别文本 + 关键词高亮 + 脉冲动画
- `processing` → 检测到关键词后的处理状态
- `completed` → 本次触发的关键词 + 识别文本

**特殊行为：** 唯一有 `fulltext` tab 的节点 — 展示所有历史识别文本的累积记录。

---

## 4. `stt_history` — STT 历史 + 关键词判断

| 维度 | 内容 |
|---|---|
| 功能 | 累积 STT 文本历史，判断是否含关键词，决定是否触发下游 |
| 类别 | Transform |
| 执行模式 | One-shot（但跨执行累积状态） |
| 写 accumulated_context | **`stt_history`** — `list[str]`，上限 `max_entries` |

**元数据：** icon=`history_edu`, color=`tertiary`

**端口：**

| 方向 | id | data_type | 可见 | 说明 |
|---|---|---|---|---|
| 入 | `hist-in` | `string` | always | 文本片段 |
| 入 | `trigger-in` | `event` | on-demand | 触发 |
| 出 | `hist-out` | `string_array` | always | 完整历史数组 |
| 出 | `hist-trigger` | `event` | always | 关键词触发信号 |
| 出 | `done` | `event` | on-demand | 完成信号 |

**配置：**
- `max_entries`: `20` — 最大历史条数
- `context_window`: `128000` — 上下文窗口大小

**标签页：** `config`、`detail`、`io-data`、`io-mgmt`、`log`

**输出条件：**
- 含关键词 → `{history, trigger_keyword, condition_result: "matched"}`
- 不含关键词 → `{history, condition_result: "skipped"}`
- 未配置关键词 → `{history}`

---

## 5. `context_build` — 上下文组装

| 维度 | 内容 |
|---|---|
| 功能 | 从多个来源组装 LLM 所需的消息数组 |
| 类别 | Transform |
| 执行模式 | One-shot |
| 写 accumulated_context | 否（只读） |

**元数据：** icon=`hub`, color=`primary`

**端口：**

| 方向 | id | data_type | 可见 | 说明 |
|---|---|---|---|---|
| 入 | `ctx-in1` | `string` | always | skill_prompt |
| 入 | `ctx-in2` | `string` | on-demand | OCR 文本 |
| 入 | `ctx-in3` | `string_array` | on-demand | stt_history |
| 入 | `ctx-in4` | `string_array` | on-demand | 对话历史 |
| 入 | `trigger-in` | `event` | on-demand | 触发 |
| 出 | `ctx-out` | `messages` | always | 组装后的消息数组 |
| 出 | `done` | `event` | on-demand | 完成信号 |

**配置：**
- `max_context_length`: `4096` — 最大上下文长度

**标签页：** `config`、`detail`、`io-data`、`io-mgmt`、`log`

**数据来源优先级：**
- `skill_prompt` → 从连线读取，或从 `accumulated_context["skill_prompt"]` 读取
- OCR 文本 → 从连线读取，或从 `accumulated_context["ocr_texts"]` 读取
- STT 历史 → 从连线读取，或从 `accumulated_context["stt_history"]` 读取
- 对话历史 → 从 `accumulated_context["llm_messages"]` 读取最近 6 条

**输出结构：** `{messages: [{role, content}, ...], ocr_text, stt_text}`

---

## 6. `llm` — LLM 生成

| 维度 | 内容 |
|---|---|
| 功能 | 调用 LLM API 流式生成回复 |
| 类别 | Transform |
| 执行模式 | One-shot（内部流式但整体一次性返回） |
| 写 accumulated_context | **`llm_messages`** — `list[{role, content}]`，上限 20 条 |

**元数据：** icon=`smart_toy`, color=`primary`

**端口：**

| 方向 | id | data_type | 可见 | 说明 |
|---|---|---|---|---|
| 入 | `llm-in` | `messages` | always | 消息数组 |
| 入 | `trigger-in` | `event` | on-demand | 触发 |
| 出 | `llm-out` | `string` | always | 生成文本 |
| 出 | `done` | `event` | on-demand | 完成信号 |
| 出 | `meta-token-count` | `number` | on-demand | Token 消耗 |
| 出 | `meta-reasoning` | `string` | on-demand | 思考过程 |
| 出 | `meta-model` | `string` | on-demand | 使用的模型名 |

**配置：**
- `model`: `"gpt-4-turbo"` — 模型名
- `temperature`: `0.7` — 温度
- `max_tokens`: `2048` — 最大 token 数

**标签页：** `config`、`detail`、`io-data`、`io-mgmt`、`log`

**Flow Mode body：**
- `processing` → 流式文本实时显示 + 光标闪烁动画
- `completed` → 完整回复 + reasoning 折叠区

---

## 7. `tts` — TTS 合成

| 维度 | 内容 |
|---|---|
| 功能 | 将文本按句分割，逐句合成语音 |
| 类别 | Transform |
| 执行模式 | One-shot（逐句串行合成） |
| 写 accumulated_context | 否 |

**元数据：** icon=`record_voice_over`, color=`outline`

**端口：**

| 方向 | id | data_type | 可见 | 说明 |
|---|---|---|---|---|
| 入 | `tts-in` | `string` | always | 待合成文本 |
| 入 | `trigger-in` | `event` | on-demand | 触发 |
| 出 | `tts-out` | `audio` | always | 合成音频（WAV segments） |
| 出 | `done` | `event` | on-demand | 完成信号 |

**配置：**
- `engine`: `"edge"` — TTS 引擎（edge / minimax）
- `voice`: `"zh-CN-YunxiNeural"` — 语音角色
- `speed`: `1.0` — 语速

**标签页：** `config`、`detail`、`io-data`、`io-mgmt`、`log`

**输出结构：** `{segments: [{text, audio_b64, index}, ...], text, total_segments}`

---

## 8. `ts_output` — TS 音频输出

| 维度 | 内容 |
|---|---|
| 功能 | 将音频分段发送到 TeamSpeak 播放 |
| 类别 | Sink（终点） |
| 执行模式 | One-shot（逐段发送，间隔 0.2s） |
| 写 accumulated_context | 否 |

**元数据：** icon=`volume_up`, color=`secondary`

**端口：**

| 方向 | id | data_type | 可见 | 说明 |
|---|---|---|---|---|
| 入 | `out-in` | `audio` | always | 音频数据 |
| 入 | `trigger-in` | `event` | on-demand | 触发 |
| 出 | `out-done` | `event` | always | 播放完成信号 |

**配置：**
- `mode`: `"segment"` — 播放模式

**标签页：** `detail`、`io-data`、`io-mgmt`、`log` — 没有 config tab

---

## 9. `ts_input` — TS 音频输入

| 维度 | 内容 |
|---|---|
| 功能 | 订阅 AudioBus，累积音频帧到缓冲区上限后输出 |
| 类别 | Source / Listener |
| 执行模式 | **Listener（无限循环）** — 缓冲区满才 break |
| 写 accumulated_context | 否 |

**元数据：** icon=`headset_mic`, color=`secondary`

**端口：**

| 方向 | id | data_type | 可见 | 说明 |
|---|---|---|---|---|
| 入 | `trigger-in` | `event` | on-demand | 手动触发 |
| 出 | `audio-out` | `audio` | always | 音频帧数据 |
| 出 | `trigger-out` | `event` | always | 触发信号 |

**配置：**
- `max_buffer_bytes`: `10485760` (10MB) — 缓冲区上限
- `sample_rate`: `16000`
- `channels`: `1`

**标签页：** `config`、`detail`、`io-data`、`io-mgmt`、`log`

---

## 汇总

### 标签页覆盖

| 节点 | config | detail | log | fulltext | io-data | io-mgmt |
|---|---|---|---|---|---|---|
| `input_image` | — | ✓ | — | — | ✓ | — |
| `ocr` | ✓ | ✓ | ✓ | — | ✓ | ✓ |
| `stt_listen` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `stt_history` | ✓ | ✓ | ✓ | — | ✓ | ✓ |
| `context_build` | ✓ | ✓ | ✓ | — | ✓ | ✓ |
| `llm` | ✓ | ✓ | ✓ | — | ✓ | ✓ |
| `tts` | ✓ | ✓ | ✓ | — | ✓ | ✓ |
| `ts_output` | — | ✓ | ✓ | — | ✓ | ✓ |
| `ts_input` | ✓ | ✓ | ✓ | — | ✓ | ✓ |

### 执行模式与触发

| 节点 | 类别 | 循环 | 有 trigger-in | 有数据输入 |
|---|---|---|---|---|
| `input_image` | Source | 一次性 | ✗ | ✗ |
| `ocr` | Transform | 一次性 | ✓(按需) | ✓ |
| `stt_listen` | Listener | **无限循环** | ✗ | ✓(AudioBus) |
| `stt_history` | Transform | 一次性(跨执行累积) | ✓(按需) | ✓ |
| `context_build` | Transform | 一次性 | ✓(按需) | ✓ |
| `llm` | Transform | 一次性(内部流式) | ✓(按需) | ✓ |
| `tts` | Transform | 一次性 | ✓(按需) | ✓ |
| `ts_output` | Sink | 一次性 | ✓(按需) | ✓ |
| `ts_input` | Source/Listener | **无限循环** | ✓(按需) | ✗ |

### accumulated_context 写入者

| Key | 写入者 | 类型 | 说明 |
|---|---|---|---|
| `stt_history` | `stt_history` 节点 | `list[str]` | 累积的 STT 文本条目 |
| `llm_messages` | `llm` 节点 | `list[{role, content}]` | 结构化对话历史 |
| `skill_prompt` | engine.start_pipeline | `str` | 流程启动时从 Flow JSON 写入 |
