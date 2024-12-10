import numpy as np
import wave
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from scipy.signal import correlate
from scipy.fft import fft
import librosa


def extract_audio_data(input_file):
    output_file = "output.wav"
    command = [
        "ffmpeg", "-i", input_file, "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "1", output_file
    ]
    subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return output_file


def read_waveform(wav_file):
    with wave.open(wav_file, "rb") as wav:
        sample_rate = wav.getframerate()
        n_frames = wav.getnframes()
        raw_data = wav.readframes(n_frames)
        data = np.frombuffer(raw_data, dtype=np.int16)
    return sample_rate, data


def split_into_segments(data, sample_rate, bpm, bars=8, max_segments=50):
    samples_per_bar = int((60 / bpm) * sample_rate)
    samples_per_segment = samples_per_bar * bars
    n_segments = len(data) // samples_per_segment
    n_segments = min(n_segments, max_segments)  # Limit to max_segments
    print(f"Splitting data into {n_segments} segments, each {samples_per_segment} samples long.")
    return [data[i * samples_per_segment:(i + 1) * samples_per_segment] for i in range(n_segments)]


def calculate_repetitiveness(segment, sample_rate, max_lags=100, debug=False):
    """
    Calculate repetitiveness of a segment using harmonic-percussive separation and combined metrics:
    - Autocorrelation for temporal repetition
    - Frequency analysis for steady patterns
    - Beat strength for rhythmic regularity
    """
    if len(segment) == 0:
        return float("-inf")  # Invalid segment

    if debug:
        print(f"Analyzing segment of size {len(segment)} samples.")

    # Convert to librosa-compatible format (float32)
    segment = segment.astype(np.float32) / np.max(np.abs(segment))

    # Perform harmonic-percussive separation
    percussive = librosa.effects.hpss(segment)[1]

    # Downsample percussive component for performance
    downsample_factor = 10
    percussive = percussive[::downsample_factor]

    # Normalize segment
    percussive = percussive - np.mean(percussive)

    # 1. Autocorrelation Metric
    autocorr = correlate(percussive, percussive, mode='full', method='auto')
    autocorr = autocorr[len(autocorr) // 2:len(autocorr) // 2 + max_lags]
    autocorr /= np.max(np.abs(autocorr))  # Normalize
    autocorr_score = np.sum(autocorr[1:])  # Ignore lag-0

    # 2. Frequency Domain Metric (FFT)
    freqs = fft(percussive)
    magnitude = np.abs(freqs)
    freq_range = magnitude[:len(magnitude) // 2]  # Use positive frequencies
    freq_score = np.sum(freq_range[100:1000])  # Focus on 60Hz–2kHz range

    # 3. Beat Strength Metric
    onset_env = librosa.onset.onset_strength(y=percussive, sr=sample_rate)
    beat_strength = np.mean(onset_env)

    # Combine Metrics
    repetitiveness_score = autocorr_score + freq_score * 0.5 + beat_strength * 0.5

    if debug:
        print(f"Autocorr Score: {autocorr_score:.2f}, Freq Score: {freq_score:.2f}, Beat Strength: {beat_strength:.2f}")
        print(f"Combined Repetitiveness Score: {repetitiveness_score:.2f}")

    return repetitiveness_score


def analyze_segments_sequential(segments, sample_rate, debug=False):
    """
    Analyze segments sequentially for repetitiveness.
    """
    results = []
    print(f"Analyzing {len(segments)} segments sequentially...")
    for idx, segment in enumerate(segments):
        try:
            print(f"Analyzing segment {idx + 1}/{len(segments)}...")
            result = calculate_repetitiveness(segment, sample_rate, debug=debug)
            results.append(result)
            print(f"Segment {idx + 1} analyzed: Repetitiveness Score = {result:.2f}")
        except Exception as e:
            results.append(float("-inf"))
            print(f"Error analyzing segment {idx + 1}: {e}")
    return results


def format_time(seconds):
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes}:{remaining_seconds:05.2f}"


def detect_bpm(input_file):
    try:
        y, sr = librosa.load(input_file, sr=None)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)

        if isinstance(tempo, np.ndarray):  # Ensure tempo is scalar
            tempo = float(tempo[0])

        if tempo < 40:  # Validate BPM
            print(f"Warning: Detected BPM {tempo:.2f} is unrealistically low. Using fallback.")
            return 120.0  # Fallback default BPM

        return tempo
    except Exception as e:
        print(f"Error detecting BPM: {e}")
        return 120.0  # Fallback default BPM


def analyze_for_mix(input_file, bpm=None, bars=8):
    if bpm is None:
        bpm = detect_bpm(input_file)
        if bpm < 40:  # Ensure valid BPM
            raise ValueError("Invalid BPM detected or provided.")

    print(f"Using BPM: {float(bpm):.2f}")

    wav_file = extract_audio_data(input_file)
    sample_rate, data = read_waveform(wav_file)

    # Split into segments
    segments = split_into_segments(data, sample_rate, bpm, bars)
    if not segments:
        raise ValueError("Audio file is too short to create even a single segment.")

    print(f"Analyzing {len(segments)} segments sequentially for debugging...")

    # Sequentially analyze repetitiveness for debugging
    repetitiveness_scores = analyze_segments_sequential(segments, sample_rate, debug=True)
    most_repetitive_index = np.argmax(repetitiveness_scores)

    segment_length_seconds = len(segments[0]) / sample_rate

    # Most repetitive segment
    repetitive_mix_in_seconds = most_repetitive_index * segment_length_seconds
    repetitive_mix_out_seconds = repetitive_mix_in_seconds + segment_length_seconds
    repetitive_mix_in_time = format_time(repetitive_mix_in_seconds)
    repetitive_mix_out_time = format_time(repetitive_mix_out_seconds)

    if os.path.exists(wav_file):
        os.remove(wav_file)

    print("Mix Points:")
    print(f"Most Repetitive Segment: Mix-in at {repetitive_mix_in_time}, Mix-out at {repetitive_mix_out_time}")

    return {
        "most_repetitive": {
            "index": most_repetitive_index,
            "mix_in_time": repetitive_mix_in_time,
            "mix_out_time": repetitive_mix_out_time,
        },
    }
