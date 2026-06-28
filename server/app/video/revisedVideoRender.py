"""
PROTOTYPE 2
===========
Second prototype of sheet music to video renderer.
Integrated with absolute structural path routing components.
"""

import math
import os
from pathlib import Path
from threading import Thread

import cv2
import numpy as np
import pretty_midi
from midi2audio import FluidSynth
from moviepy import AudioFileClip, VideoClip, concatenate_videoclips
from music21 import *

FPS = 30
FRAME_SIZE = 6
WHITE_SIZE = 24
BLACK_SIZE = round(WHITE_SIZE * 7 / 12)

BLACK_KEY_INDEXES = [1, 3, 6, 8, 10]
WHITE_KEY_INDEXES = [0, 2, 4, 5, 7, 9, 11]

PIANO_HEIGHT = 144
SCREEN_WIDTH = 52 * WHITE_SIZE
SCREEN_HEIGHT = 702
FRAMES_ON_SCREEN = round((SCREEN_HEIGHT - PIANO_HEIGHT) / FRAME_SIZE)


class VideoRender(Thread):
    def __init__(
        self,
        file_name: str,
        file_id: str,
        chunk_id: str,
        output_file: str,
        sound_font=None,
    ):
        super().__init__(target=self.render)
        self.file_id = file_id
        self.chunk_id = chunk_id

        # 1. Dynamically compute the absolute path to your 'app/tmp' folder
        # This resolves relative paths correctly regardless of working directory
        current_file_dir = Path(__file__).resolve().parent
        self.tmp_dir = current_file_dir.parent / "tmp"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)  # Ensure it exists!

        # Isolate names cleanly without hanging extensions
        base_name, _ = os.path.splitext(file_name)
        out_name, _ = os.path.splitext(output_file)

        # 2. Harmonize your temp paths so everyone writes to and reads from the exact same files
        self.temp_midi_path = str(self.tmp_dir / f"{base_name}.mid")
        self.temp_wav_path = str(self.tmp_dir / f"{base_name}.wav")
        self.final_mp4_path = str(self.tmp_dir / f"{out_name}.mp4")

        # Dynamic soundfont location mapping
        if sound_font is None:
            self.sound_font = str(current_file_dir / "piano.sf3")
        else:
            self.sound_font = sound_font

        self.midi_array = None
        self.canvas = np.zeros((SCREEN_HEIGHT, SCREEN_WIDTH, 3), dtype=np.uint8)
        self.notes_screen = np.zeros(
            (SCREEN_HEIGHT - PIANO_HEIGHT, SCREEN_WIDTH, 3), dtype=np.uint8
        )

    def _create_midi(self):
        """Converts the musicxml file into a MIDI file"""
        sheet_music_file = converter.parse(
            "https://pub-41087431ab634ba8a456c9a62333ea39.r2.dev/raw_89302b32-ccab-4f10-8e32-2a6eb4952465_chunk_0.xml"
        )
        sheet_music_file.write(fmt="midi", fp=self.temp_midi_path)

    def _create_audio(self):
        """Converts the MIDI file into a WAV file"""
        fs = FluidSynth("piano.sf3")
        fs.midi_to_audio(self.temp_midi_path, self.temp_wav_path)

    def _load_midi_data(self):
        """Loads the MIDI data into a Numpy array"""
        midi_data = pretty_midi.PrettyMIDI(self.temp_midi_path)
        self.midi_array = np.zeros(
            (round(midi_data.get_end_time() * FPS) + 1, 128), dtype=int
        )

        for instrument in midi_data.instruments:
            if not instrument.is_drum:
                for note in instrument.notes:
                    end = math.floor(note.end * FPS)
                    for i in range(math.ceil(note.start * FPS), end + 1):
                        if i < self.midi_array.shape[0]:
                            self.midi_array[i][note.pitch] = end + 1 - i

    def _is_black(self, value):
        if value % 12 in BLACK_KEY_INDEXES:
            return value % 12
        return -1

    def _is_white(self, value):
        if value % 12 in WHITE_KEY_INDEXES:
            return WHITE_KEY_INDEXES.index(value % 12)
        return -1

    def _draw_keyboard(self, offset):
        cv2.rectangle(
            self.canvas,
            (0, SCREEN_HEIGHT - PIANO_HEIGHT),
            (SCREEN_WIDTH, SCREEN_HEIGHT),
            (255, 255, 255),
            -1,
        )

        if 0 < offset <= self.midi_array.shape[0]:
            for note in range(128):
                if self.midi_array[offset - 1][note] > 0 and self._is_white(note) != -1:
                    octave = math.floor(note / 12) * 7 * WHITE_SIZE - 12 * WHITE_SIZE
                    x = octave + WHITE_SIZE * self._is_white(note)
                    cv2.rectangle(
                        self.canvas,
                        (x, SCREEN_HEIGHT - PIANO_HEIGHT),
                        (x + WHITE_SIZE, SCREEN_HEIGHT),
                        (250, 128, 0),
                        -1,
                    )

        for i in range(52):
            cv2.rectangle(
                self.canvas,
                (i * WHITE_SIZE, SCREEN_HEIGHT - PIANO_HEIGHT),
                ((i + 1) * WHITE_SIZE, SCREEN_HEIGHT),
                (0, 0, 0),
                1,
            )

        cv2.rectangle(
            self.canvas,
            ((2 * WHITE_SIZE) - (BLACK_SIZE * 2), SCREEN_HEIGHT - PIANO_HEIGHT),
            ((2 * WHITE_SIZE) - BLACK_SIZE, round(SCREEN_HEIGHT - (PIANO_HEIGHT / 2))),
            (0, 0, 0),
            -1,
        )

        for octave in range(7):
            for i in range(12):
                if i in [1, 3, 6, 8, 10]:
                    p1 = WHITE_SIZE * 2 + octave * WHITE_SIZE * 7 + BLACK_SIZE * i
                    p2 = p1 + BLACK_SIZE
                    cv2.rectangle(
                        self.canvas,
                        (p1, SCREEN_HEIGHT - PIANO_HEIGHT),
                        (p2, round(SCREEN_HEIGHT - (PIANO_HEIGHT / 2))),
                        (0, 0, 0),
                        -1,
                    )

        if 0 < offset <= self.midi_array.shape[0]:
            for note in range(128):
                if self.midi_array[offset - 1][note] > 0 and self._is_black(note) != -1:
                    octave = math.floor(note / 12) * 7 * WHITE_SIZE - 12 * WHITE_SIZE
                    x = octave + BLACK_SIZE * self._is_black(note)
                    cv2.rectangle(
                        self.canvas,
                        (x, SCREEN_HEIGHT - PIANO_HEIGHT),
                        (x + BLACK_SIZE, round(SCREEN_HEIGHT - (PIANO_HEIGHT / 2))),
                        (0, 128, 250),
                        -1,
                    )

    def _draw_notes(self, offset):
        cv2.rectangle(
            self.notes_screen,
            (0, 0),
            (self.notes_screen.shape[1], self.notes_screen.shape[0]),
            (16, 16, 16),
            -1,
        )

        for i in range(offset, offset + FRAMES_ON_SCREEN):
            if i < 0 or i >= self.midi_array.shape[0]:
                continue

            for note in range(128):
                if self.midi_array[i][note] == 0:
                    continue

                octave = math.floor(note / 12) * 7 * WHITE_SIZE - 12 * WHITE_SIZE

                if self._is_white(note) != -1:
                    x = octave + WHITE_SIZE * self._is_white(note)
                    cv2.rectangle(
                        self.notes_screen,
                        (x, (i - offset) * FRAME_SIZE),
                        (
                            x + WHITE_SIZE,
                            (i - offset + self.midi_array[i][note]) * FRAME_SIZE - 1,
                        ),
                        (250, 128, 0),
                        -1,
                    )
                elif self._is_black(note) != -1:
                    x = octave + BLACK_SIZE * self._is_black(note)
                    cv2.rectangle(
                        self.notes_screen,
                        (x, (i - offset) * FRAME_SIZE),
                        (
                            x + BLACK_SIZE,
                            (i - offset + self.midi_array[i][note]) * FRAME_SIZE - 1,
                        ),
                        (0, 128, 250),
                        -1,
                    )

        self.canvas[0 : SCREEN_HEIGHT - PIANO_HEIGHT, 0:SCREEN_WIDTH] = cv2.flip(
            self.notes_screen, 0
        )

    def _make_frames(self, t):
        offset = int(t * FPS) - FRAMES_ON_SCREEN
        self._draw_notes(offset)
        self._draw_keyboard(offset)
        return np.asarray(
            cv2.cvtColor(self.canvas, cv2.COLOR_BGR2RGB)[:, :], dtype=np.uint8
        )

    def render(self):
        self._create_midi()
        self._create_audio()
        self._load_midi_data()

        # Context wrapping with safe 'with' tags keeps MoviePy stable and clears the proc bugs
        with AudioFileClip(self.temp_wav_path) as audio:
            duration = (self.midi_array.shape[0] + (2 * FRAMES_ON_SCREEN)) / FPS

            with VideoClip(self._make_frames, duration=duration) as clip:
                clip1 = clip.subclipped(0, FRAMES_ON_SCREEN / FPS)
                clip2 = clip.subclipped(
                    FRAMES_ON_SCREEN / FPS, clip.duration
                ).with_audio(audio)

                with concatenate_videoclips([clip1, clip2]) as final_video:
                    final_video.write_videofile(self.final_mp4_path, fps=FPS, threads=4)

        # Clear environmental temp assets after compiling video container files
        for path in [self.temp_wav_path, self.temp_midi_path]:
            if os.path.exists(path):
                os.remove(path)


if __name__ == "__main__":
    # Test block triggers perfectly now
    VideoRender(
        file_name="raw_chunk_test_0.xml",
        file_id="89302b32-ccab-4f10-8e32-2a6eb4952465",
        chunk_id="0",
        output_file="raw_chunk.mp4",
    ).render()
