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
    n_segments = min(n_segments, max_segments) 
    return [data[i * samples_per_segment:(i + 1) * samples_per_segment] for i in range(n_segments)]


def calculate_repetitiveness(segment, sample_rate, max_lags=100, debug=False):
    """
    Analyes segments in terms of repetitiveness, vocal intensity and loudness
    """
    if len(segment) == 0:
        return float("-inf") 


    segment = segment.astype(np.float32) / np.max(np.abs(segment))

    harmonic, percussive = librosa.effects.hpss(segment)

    vocal_intensity = np.sum(np.abs(harmonic)) / (np.sum(np.abs(harmonic)) + np.sum(np.abs(percussive)))

    rms_energy = np.mean(librosa.feature.rms(y=segment))

    percussive = percussive[::10]
    percussive -= np.mean(percussive)

   
    autocorr = correlate(percussive, percussive, mode='full', method='auto')
    autocorr = autocorr[len(autocorr) // 2:len(autocorr) // 2 + max_lags]
    autocorr /= np.max(np.abs(autocorr)) 
    autocorr_score = np.sum(autocorr[1:])  

    freqs = fft(percussive)
    magnitude = np.abs(freqs)
    freq_score = np.sum(magnitude[100:1000])  

    onset_env = librosa.onset.onset_strength(y=percussive, sr=sample_rate)
    beat_strength = np.mean(onset_env)

    repetitiveness_score = autocorr_score + freq_score * 0.5 + beat_strength * 0.5

    final_score = (
        repetitiveness_score * 0.5 
        - vocal_intensity * 0.3   
        - rms_energy * 0.2        
    )

    return final_score


def analyze_segments_sequential(segments, sample_rate, debug=False):
    """
    Analyze segments for repetitiveness
    """
    results = []
    for idx, segment in enumerate(segments):
        try:
            result = calculate_repetitiveness(segment, sample_rate, debug=debug)
            results.append(result)
        except Exception as e:
            results.append(float("-inf"))
            print(f"Error analyzing segment {idx + 1}: {e}")
    return results


def format_time(seconds):
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes}:{remaining_seconds:05.2f}"

def detect_bpm(input_file, max_duration=30.0, segment_count=5):
    try:
        y, sr = librosa.load(input_file, sr=None, mono=True, duration=max_duration)

        y_percussive = librosa.effects.percussive(y)

        total_samples = len(y_percussive)
        segment_size = total_samples // segment_count
        bpm_values = []

        for i in range(segment_count):
            start = i * segment_size
            end = min((i + 1) * segment_size, total_samples)
            segment = y_percussive[start:end]

            onset_env = librosa.onset.onset_strength(y=segment, sr=sr, aggregate=np.median)

            tempo, beat_frames = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
            bpm_values.append(tempo)

        refined_bpm = np.median(bpm_values)

        beat_intervals = []
        for tempo, segment in zip(bpm_values, range(segment_count)):
            onset_env = librosa.onset.onset_strength(y=y_percussive, sr=sr, aggregate=np.median)
            _, beat_frames = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
            beat_times = librosa.frames_to_time(beat_frames, sr=sr)
            if len(beat_times) > 1:
                intervals = np.diff(beat_times)
                interval_tempo = 60.0 / np.mean(intervals)
                beat_intervals.append(interval_tempo)

        if beat_intervals:
            refined_bpm = np.median(beat_intervals)

        refined_bpm = round(refined_bpm, 1)
        print(f"Detected BPM: {refined_bpm}")
        return refined_bpm

    except Exception as e:
        print(f"Error detecting BPM: {e}")
        return 120.0  


def bestMix_for_audio(input_file, bpm=None, bars=8):

    if bpm is None:
        bpm = detect_bpm(input_file)
        if bpm < 40: 
            raise ValueError("Invalid BPM detected or provided.")

    print(f"Using BPM: {float(bpm):.2f}")

    wav_file = extract_audio_data(input_file)
    sample_rate, data = read_waveform(wav_file)

    segments = split_into_segments(data, sample_rate, bpm, bars)
    if not segments:
        raise ValueError("Audio file is too short to create even a single segment.")


    repetitiveness_scores = analyze_segments_sequential(segments, sample_rate, debug=True)
    most_repetitive_index = np.argmax(repetitiveness_scores)

    segment_length_seconds = len(segments[0]) / sample_rate

    repetitive_mix_in_seconds = most_repetitive_index * segment_length_seconds
    mix_out_duration_seconds = (32 / bpm) * 60 
    repetitive_mix_out_seconds = repetitive_mix_in_seconds + mix_out_duration_seconds

    repetitive_mix_in_time = format_time(repetitive_mix_in_seconds)
    repetitive_mix_out_time = format_time(repetitive_mix_out_seconds)

    if os.path.exists(wav_file):
        os.remove(wav_file)

    print("\nMix Points:")
    print(f"Best Segment: Mix-in at {repetitive_mix_in_time}, Mix-out at {repetitive_mix_out_time}")

    return {
        "most_repetitive": {
            "index": most_repetitive_index,
            "mix_in_time": repetitive_mix_in_time,
            "mix_out_time": repetitive_mix_out_time,
        },
    }
