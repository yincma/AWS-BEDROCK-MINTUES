#!/usr/bin/env python3
"""
生成有效的MP3测试文件

使用wave和lame编码器创建真实的MP3音频文件
如果lame不可用，则使用pydub，如果pydub也不可用，则创建最小的有效MP3结构
"""
import os
import struct
import wave
import subprocess

def create_wav_file(filename, duration_seconds=5, sample_rate=44100):
    """创建WAV文件"""
    num_samples = duration_seconds * sample_rate

    with wave.open(filename, 'w') as wav_file:
        # 设置参数：1通道，2字节采样宽度，44.1kHz采样率
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        # 生成静音音频数据
        for i in range(num_samples):
            # 写入16位PCM静音（值为0）
            wav_file.writeframes(struct.pack('<h', 0))

    print(f"✓ 创建WAV文件: {filename}")


def convert_wav_to_mp3_with_lame(wav_file, mp3_file):
    """使用lame将WAV转换为MP3"""
    try:
        result = subprocess.run(
            ['lame', '--preset', 'standard', wav_file, mp3_file],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            print(f"✓ 使用lame转换为MP3: {mp3_file}")
            return True
        else:
            print(f"✗ lame转换失败: {result.stderr}")
            return False
    except FileNotFoundError:
        print("✗ lame未安装")
        return False
    except Exception as e:
        print(f"✗ lame转换出错: {e}")
        return False


def convert_wav_to_mp3_with_pydub(wav_file, mp3_file):
    """使用pydub将WAV转换为MP3"""
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_wav(wav_file)
        audio.export(mp3_file, format="mp3", bitrate="128k")
        print(f"✓ 使用pydub转换为MP3: {mp3_file}")
        return True
    except ImportError:
        print("✗ pydub未安装")
        return False
    except Exception as e:
        print(f"✗ pydub转换出错: {e}")
        return False


def create_minimal_valid_mp3(filename):
    """
    创建最小的有效MP3文件

    这个文件包含有效的MP3帧头和一些静音数据
    虽然非常短，但足以通过mutagen和其他MP3解析器的验证
    """
    # MP3帧头结构（MPEG-1 Layer 3, 128kbps, 44.1kHz, 单声道）
    # 0xFFFB: 同步字 + MPEG版本 + Layer
    # 0x90: 比特率索引 + 采样率索引
    # 0x00: 填充位 + 私有位 + 声道模式
    # 0x00: 模式扩展 + 版权 + 原始 + 强调

    mp3_frame_header = bytes([0xFF, 0xFB, 0x90, 0x00])

    # 一个完整的MP3帧大小（128kbps @ 44.1kHz）约为417字节
    # 创建多个帧以确保文件有效
    frame_size = 417
    num_frames = 25  # 约1秒的音频

    with open(filename, 'wb') as f:
        # 写入ID3v2标签（可选，但有助于兼容性）
        id3v2_header = b'ID3\x03\x00\x00\x00\x00\x00\x00'  # 最小ID3v2标签
        f.write(id3v2_header)

        # 写入MP3帧
        for _ in range(num_frames):
            f.write(mp3_frame_header)
            # 填充帧数据（静音）
            f.write(b'\x00' * (frame_size - 4))

    print(f"✓ 创建最小有效MP3: {filename}")
    return True


def main():
    """主函数"""
    fixtures_dir = os.path.dirname(os.path.abspath(__file__))

    # 文件路径
    short_wav = os.path.join(fixtures_dir, 'temp_short.wav')
    short_mp3 = os.path.join(fixtures_dir, 'test_short.mp3')
    long_wav = os.path.join(fixtures_dir, 'temp_long.wav')
    long_mp3 = os.path.join(fixtures_dir, 'test_long.mp3')

    print("=" * 60)
    print("生成测试MP3文件")
    print("=" * 60)
    print()

    # 尝试方法1: WAV + lame
    print("方法1: 尝试使用WAV + lame...")
    create_wav_file(short_wav, duration_seconds=5)
    if convert_wav_to_mp3_with_lame(short_wav, short_mp3):
        create_wav_file(long_wav, duration_seconds=120)
        convert_wav_to_mp3_with_lame(long_wav, long_mp3)
        # 清理临时WAV文件
        os.remove(short_wav)
        os.remove(long_wav)
        print()
        print("✓ 成功使用lame创建MP3文件")
        return

    # 尝试方法2: pydub
    print()
    print("方法2: 尝试使用pydub...")
    if convert_wav_to_mp3_with_pydub(short_wav, short_mp3):
        create_wav_file(long_wav, duration_seconds=120)
        convert_wav_to_mp3_with_pydub(long_wav, long_mp3)
        # 清理临时WAV文件
        os.remove(short_wav)
        os.remove(long_wav)
        print()
        print("✓ 成功使用pydub创建MP3文件")
        return

    # 清理临时WAV文件
    if os.path.exists(short_wav):
        os.remove(short_wav)
    if os.path.exists(long_wav):
        os.remove(long_wav)

    # 方法3: 创建最小有效MP3
    print()
    print("方法3: 创建最小有效MP3结构...")
    create_minimal_valid_mp3(short_mp3)
    # 长文件：重复多次以增加大小
    with open(short_mp3, 'rb') as f:
        short_data = f.read()
    with open(long_mp3, 'wb') as f:
        for _ in range(50):  # 重复50次
            f.write(short_data)
    print(f"✓ 创建长MP3文件: {long_mp3}")

    print()
    print("=" * 60)
    print("✓ 测试MP3文件生成完成")
    print("=" * 60)
    print()
    print(f"文件位置:")
    print(f"  - 短音频: {short_mp3}")
    print(f"  - 长音频: {long_mp3}")


if __name__ == "__main__":
    main()
