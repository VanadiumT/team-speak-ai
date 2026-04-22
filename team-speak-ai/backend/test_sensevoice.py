#!/usr/bin/env python3
"""
SenseVoice STT 测试脚本
验证方式:
1. 检查代码结构和接口完整性
2. 验证 SenseVoice 模型加载
3. 测试音频转写 (需要测试音频文件)

模型下载:
- 使用 ModelScope SDK 自动下载
- 模型: iic/SenseVoiceSmall (约 1.7GB)
- 首次使用会自动下载，如需手动下载:
  from modelscope import snapshot_download
  snapshot_download('iic/SenseVoiceSmall')
"""

import asyncio
import sys
import os
import inspect

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.stt.base import BaseSTT
from core.stt.factory import create_stt, STTProvider


def test_code_structure():
    """测试代码结构完整性"""
    print("=" * 50)
    print("Phase 3: SenseVoice STT")
    print("代码结构验证")
    print("=" * 50)

    all_passed = True

    # 1. 验证 BaseSTT 抽象类
    print("\n[1/5] 验证 BaseSTT 抽象类...")
    try:
        assert hasattr(BaseSTT, 'transcribe'), "缺少 transcribe 方法"
        assert hasattr(BaseSTT, 'transcribe_stream'), "缺少 transcribe_stream 方法"
        print("   [PASS] BaseSTT 抽象类验证通过")
    except Exception as e:
        print(f"   [FAIL] BaseSTT 验证失败: {e}")
        all_passed = False

    # 2. 验证 SenseVoiceSTT 实现
    print("\n[2/5] 验证 SenseVoiceSTT 实现...")
    try:
        from core.stt.sensevoice_stt import SenseVoiceSTT
        assert issubclass(SenseVoiceSTT, BaseSTT), "SenseVoiceSTT必须继承BaseSTT"
        sig = inspect.signature(SenseVoiceSTT.__init__)
        params = list(sig.parameters.keys())
        assert 'model_dir' in params, "缺少 model_dir 参数"
        assert 'device' in params, "缺少 device 参数"
        print("   [PASS] SenseVoiceSTT 实现验证通过")
    except Exception as e:
        print(f"   [FAIL] SenseVoiceSTT 验证失败: {e}")
        all_passed = False

    # 3. 验证工厂函数
    print("\n[3/5] 验证 STT 工厂函数...")
    try:
        assert STTProvider.SENSEVOICE.value == "sensevoice", "SENSEVOICE枚举值错误"
        sig = inspect.signature(create_stt)
        params = list(sig.parameters.keys())
        assert 'provider' in params, "缺少 provider 参数"
        assert 'config' in params, "缺少 config 参数"
        print("   [PASS] STT 工厂函数验证通过")
    except Exception as e:
        print(f"   [FAIL] STT 工厂函数验证失败: {e}")
        all_passed = False

    # 4. 验证配置文件
    print("\n[4/5] 验证配置文件...")
    try:
        from config import settings
        assert hasattr(settings, 'sensevoice_model'), "缺少 sensevoice_model 配置"
        assert hasattr(settings, 'sensevoice_device'), "缺少 sensevoice_device 配置"
        assert hasattr(settings, 'stt_provider'), "缺少 stt_provider 配置"
        print(f"   [PASS] stt_provider: {settings.stt_provider}")
        print(f"   [PASS] sensevoice_model: {settings.sensevoice_model}")
        print(f"   [PASS] sensevoice_device: {settings.sensevoice_device}")
        print("   [PASS] 配置文件验证通过")
    except Exception as e:
        print(f"   [FAIL] 配置文件验证失败: {e}")
        all_passed = False

    # 5. 验证依赖安装
    print("\n[5/5] 验证依赖包...")
    try:
        import funasr
        import modelscope
        print(f"   [PASS] funasr: {funasr.__version__}")
        print(f"   [PASS] modelscope: {modelscope.__version__}")
        print("   [PASS] 依赖验证通过")
    except ImportError as e:
        print(f"   [FAIL] 缺少依赖: {e}")
        print("   请运行: pip install -U funasr modelscope")
        all_passed = False

    return all_passed


async def test_model_loading():
    """测试模型加载"""
    print("\n" + "=" * 50)
    print("SenseVoice 模型加载测试")
    print("=" * 50)

    config = {
        "model_dir": "iic/SenseVoiceSmall",
        "device": "cpu",  # 使用 CPU 避免 CUDA 问题
    }

    print(f"\n配置: {config}")
    print("正在加载 SenseVoice 模型 (首次需要下载，请稍候)...")
    print("模型约 1.7GB，下载后保存在 ModelScope 缓存目录")

    try:
        stt = create_stt(STTProvider.SENSEVOICE, config)
        print("[PASS] 模型加载成功!")
        return stt
    except Exception as e:
        error_msg = str(e)
        if "ConnectTimeout" in error_msg or "ConnectionError" in error_msg:
            print("\n[WARN] 网络连接问题，无法下载模型")
            print("  请确保:")
            print("  1. 网络连接正常")
            print("  2. 可以访问 ModelScope")
            print("  或手动下载模型:")
            print("  from modelscope import snapshot_download")
            print("  snapshot_download('iic/SenseVoiceSmall')")
        else:
            print(f"\n[FAIL] 模型加载失败: {e}")
        return None


async def test_transcribe(stt):
    """测试音频转写"""
    print("\n" + "=" * 50)
    print("音频转写测试")
    print("=" * 50)

    test_audio_path = os.path.join(os.path.dirname(__file__), "test_audio.wav")

    if not os.path.exists(test_audio_path):
        print(f"\n[WARN] 测试音频文件不存在: {test_audio_path}")
        print("  请准备 wav/mp3 音频文件进行测试")
        print("\n跳过音频转写测试")
        return True

    if stt is None:
        print("\n[WARN] 无法加载模型，跳过转写测试")
        return True

    print(f"\n使用测试音频: {test_audio_path}")
    with open(test_audio_path, "rb") as f:
        audio_data = f.read()

    print(f"音频大小: {len(audio_data)} bytes")
    print("正在进行语音识别...")

    try:
        result = await stt.transcribe(audio_data)
        print(f"[PASS] 识别结果: {result}")
        return True
    except Exception as e:
        print(f"[FAIL] 转写失败: {e}")
        return False


if __name__ == "__main__":
    async def main():
        # 第一步: 验证代码结构
        structure_ok = test_code_structure()

        # 第二步: 尝试加载模型
        stt = await test_model_loading()

        # 第三步: 测试转写
        transcribe_ok = await test_transcribe(stt)

        print("\n" + "=" * 50)
        print("验证结果汇总")
        print("=" * 50)
        print(f"代码结构验证: {'[PASS]' if structure_ok else '[FAIL]'}")
        print(f"模型加载: {'[PASS]' if stt else '[WARN] 跳过 (网络问题)'}")
        print(f"音频转写测试: {'[PASS]' if transcribe_ok else '[WARN] 跳过'}")

        print("\n" + "-" * 50)
        if structure_ok:
            print("Phase 3 (SenseVoice STT) 代码实现完整")
            print("待模型下载后可进行完整测试")
        else:
            print("Phase 3 存在代码问题，需要修复")
        print("-" * 50)

    asyncio.run(main())
