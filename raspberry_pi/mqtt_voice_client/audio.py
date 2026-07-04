"""
Audio recording and playback for Raspberry Pi

Supports multiple backends:
- sounddevice (recommended, pure Python)
- pyaudio (cross-platform, C extension)
- alsaaudio (Linux native ALSA, lightweight)
"""

import io
import logging
import wave
from typing import Optional

logger = logging.getLogger(__name__)


class AudioRecorder:
    """
    Record audio from microphone.
    
    Automatically selects best available audio backend.
    """
    
    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        dtype: str = "int16",
        backend: Optional[str] = None,
    ):
        """
        Initialize AudioRecorder.
        
        Args:
            sample_rate: Sample rate in Hz (16000 recommended for STT)
            channels: Number of channels (1=mono, 2=stereo)
            dtype: Audio data type ("int16" = PCM16)
            backend: Force specific backend ("sounddevice", "pyaudio", "alsaaudio")
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        self.backend = backend or self._detect_backend()
        
        logger.info(f"Using audio backend: {self.backend}")
    
    def _detect_backend(self) -> str:
        """Detect best available audio backend."""
        try:
            import sounddevice
            return "sounddevice"
        except ImportError:
            pass
        
        try:
            import pyaudio
            return "pyaudio"
        except ImportError:
            pass
        
        try:
            import alsaaudio
            return "alsaaudio"
        except ImportError:
            pass
        
        raise RuntimeError(
            "No audio backend available. Install one of: "
            "sounddevice, pyaudio, or alsaaudio"
        )
    
    def record(self, duration: float = 5.0) -> bytes:
        """
        Record audio for specified duration.
        
        Args:
            duration: Recording duration in seconds
        
        Returns:
            PCM16 mono audio bytes
        """
        if self.backend == "sounddevice":
            return self._record_sounddevice(duration)
        elif self.backend == "pyaudio":
            return self._record_pyaudio(duration)
        elif self.backend == "alsaaudio":
            return self._record_alsaaudio(duration)
        else:
            raise RuntimeError(f"Unknown backend: {self.backend}")
    
    def _record_sounddevice(self, duration: float) -> bytes:
        """Record using sounddevice backend."""
        import sounddevice as sd
        import numpy as np
        
        logger.info(f"Recording {duration}s audio (sounddevice)...")
        
        recording = sd.rec(
            int(duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=self.dtype,
        )
        sd.wait()
        
        # Convert to bytes
        if self.channels > 1:
            # Mix down to mono
            recording = recording.mean(axis=1, keepdims=True)
        
        audio_bytes = recording.astype('int16').tobytes()
        logger.info(f"Recorded {len(audio_bytes)} bytes")
        return audio_bytes
    
    def _record_pyaudio(self, duration: float) -> bytes:
        """Record using pyaudio backend."""
        import pyaudio
        
        logger.info(f"Recording {duration}s audio (pyaudio)...")
        
        p = pyaudio.PyAudio()
        
        stream = p.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=1024,
        )
        
        frames = []
        num_chunks = int(self.sample_rate / 1024 * duration)
        
        for i in range(num_chunks):
            data = stream.read(1024)
            frames.append(data)
        
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        audio_bytes = b''.join(frames)
        logger.info(f"Recorded {len(audio_bytes)} bytes")
        return audio_bytes
    
    def _record_alsaaudio(self, duration: float) -> bytes:
        """Record using alsaaudio backend (Linux native)."""
        import alsaaudio
        
        logger.info(f"Recording {duration}s audio (alsaaudio)...")
        
        inp = alsaaudio.PCM(
            alsaaudio.PCM_CAPTURE,
            alsaaudio.PCM_NORMAL,
            channels=self.channels,
            rate=self.sample_rate,
            format=alsaaudio.PCM_FORMAT_S16_LE,
            periodsize=1024,
        )
        
        frames = []
        num_chunks = int(self.sample_rate / 1024 * duration)
        
        for i in range(num_chunks):
            length, data = inp.read()
            if length > 0:
                frames.append(data)
        
        audio_bytes = b''.join(frames)
        logger.info(f"Recorded {len(audio_bytes)} bytes")
        return audio_bytes


class AudioPlayer:
    """
    Play audio through speaker.
    
    Automatically selects best available audio backend.
    """
    
    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        backend: Optional[str] = None,
    ):
        """
        Initialize AudioPlayer.
        
        Args:
            sample_rate: Sample rate in Hz
            channels: Number of channels (1=mono, 2=stereo)
            backend: Force specific backend ("sounddevice", "pyaudio", "alsaaudio")
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.backend = backend or self._detect_backend()
        
        logger.info(f"Using audio backend: {self.backend}")
    
    def _detect_backend(self) -> str:
        """Detect best available audio backend."""
        try:
            import sounddevice
            return "sounddevice"
        except ImportError:
            pass
        
        try:
            import pyaudio
            return "pyaudio"
        except ImportError:
            pass
        
        try:
            import alsaaudio
            return "alsaaudio"
        except ImportError:
            pass
        
        raise RuntimeError(
            "No audio backend available. Install one of: "
            "sounddevice, pyaudio, or alsaaudio"
        )
    
    def play(self, audio_bytes: bytes, sample_rate: Optional[int] = None) -> None:
        """
        Play audio.
        
        Args:
            audio_bytes: PCM16 audio data or WAV file bytes
            sample_rate: Override sample rate (auto-detect from WAV header if present)
        """
        # Try to parse as WAV file first
        try:
            with wave.open(io.BytesIO(audio_bytes), 'rb') as wf:
                sample_rate = sample_rate or wf.getframerate()
                channels = wf.getnchannels()
                audio_bytes = wf.readframes(wf.getnframes())
                
                if self.backend == "sounddevice":
                    self._play_sounddevice(audio_bytes, sample_rate, channels)
                elif self.backend == "pyaudio":
                    self._play_pyaudio(audio_bytes, sample_rate, channels)
                elif self.backend == "alsaaudio":
                    self._play_alsaaudio(audio_bytes, sample_rate, channels)
                return
        except wave.Error:
            # Not a WAV file, assume raw PCM16
            pass
        
        # Play raw PCM16
        sample_rate = sample_rate or self.sample_rate
        
        if self.backend == "sounddevice":
            self._play_sounddevice(audio_bytes, sample_rate, self.channels)
        elif self.backend == "pyaudio":
            self._play_pyaudio(audio_bytes, sample_rate, self.channels)
        elif self.backend == "alsaaudio":
            self._play_alsaaudio(audio_bytes, sample_rate, self.channels)
    
    def _play_sounddevice(
        self,
        audio_bytes: bytes,
        sample_rate: int,
        channels: int,
    ) -> None:
        """Play using sounddevice backend."""
        import sounddevice as sd
        import numpy as np
        
        logger.info(f"Playing {len(audio_bytes)} bytes (sounddevice)...")
        
        # Convert bytes to numpy array
        audio_array = np.frombuffer(audio_bytes, dtype='int16')
        
        if channels > 1:
            audio_array = audio_array.reshape(-1, channels)
        
        sd.play(audio_array, samplerate=sample_rate)
        sd.wait()
        
        logger.info("Playback finished")
    
    def _play_pyaudio(
        self,
        audio_bytes: bytes,
        sample_rate: int,
        channels: int,
    ) -> None:
        """Play using pyaudio backend."""
        import pyaudio
        
        logger.info(f"Playing {len(audio_bytes)} bytes (pyaudio)...")
        
        p = pyaudio.PyAudio()
        
        stream = p.open(
            format=pyaudio.paInt16,
            channels=channels,
            rate=sample_rate,
            output=True,
        )
        
        # Play in chunks
        chunk_size = 1024
        for i in range(0, len(audio_bytes), chunk_size):
            stream.write(audio_bytes[i:i+chunk_size])
        
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        logger.info("Playback finished")
    
    def _play_alsaaudio(
        self,
        audio_bytes: bytes,
        sample_rate: int,
        channels: int,
    ) -> None:
        """Play using alsaaudio backend (Linux native)."""
        import alsaaudio
        
        logger.info(f"Playing {len(audio_bytes)} bytes (alsaaudio)...")
        
        out = alsaaudio.PCM(
            alsaaudio.PCM_PLAYBACK,
            alsaaudio.PCM_NORMAL,
            channels=channels,
            rate=sample_rate,
            format=alsaaudio.PCM_FORMAT_S16_LE,
            periodsize=1024,
        )
        
        # Play in chunks
        chunk_size = 1024 * channels * 2  # 2 bytes per sample
        for i in range(0, len(audio_bytes), chunk_size):
            out.write(audio_bytes[i:i+chunk_size])
        
        logger.info("Playback finished")
