"""
PROTOTYPE 2
===========

Seond prototype of sheet music to video renderer.

Additions:
"""

# Imports
import math
import os
from threading import Thread

import cv2
import numpy as np
import pretty_midi

# from app.config import settings
from midi2audio import FluidSynth
from moviepy import AudioFileClip, VideoClip, VideoFileClip, concatenate_videoclips
from music21 import *

FPS = 30
"""
Frame rate of video
"""

FRAME_SIZE = 6
"""
Size in pixels of a single frame note
"""

WHITE_SIZE = 24
"""
Width of a white note
"""
BLACK_SIZE = round(WHITE_SIZE * 7 / 12)
"""
Width of a black note
"""

BLACK_KEY_INDEXES = [1, 3, 6, 8, 10]
"""
Indexes of black keys in octave
"""

WHITE_KEY_INDEXES = [0, 2, 4, 5, 7, 9, 11]
"""
Indexes of white keys in octave
"""

PIANO_HEIGHT = 144
"""
Height of piano keyboard
"""

SCREEN_WIDTH = 52 * WHITE_SIZE
SCREEN_HEIGHT = 702

FRAMES_ON_SCREEN = round((SCREEN_HEIGHT - PIANO_HEIGHT) / FRAME_SIZE)
"""
Number of note frames shown on screen
"""


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

        self.file_name, self.file_ext = os.path.splitext(file_name)

        self.output_file, _ = os.path.splitext(output_file)
        print(self.file_name, self.file_ext, self.output_file)

        self.temp_midi_path = f"app/tmp/{self.file_name}.mid"
        self.temp_wav_path = f"app/tmp/{self.file_name}.wav"

        self.sound_font: str
        if sound_font == None:
            self.sound_font = "piano.sf3"
        else:
            self.sound_font = sound_font

        self.midi_array = None
        """
        Numpy array containing MIDI notes
        """

        self.canvas = np.zeros((SCREEN_HEIGHT, SCREEN_WIDTH, 3), dtype=np.uint8)
        """
        Video canvas used for rendering each frame
        """
        self.notes_screen = np.zeros(
            (SCREEN_HEIGHT - PIANO_HEIGHT, SCREEN_WIDTH, 3), dtype=np.uint8
        )
        """
        Notes canvas for drawing the notes visible on screen
        """

    def _create_midi(self):
        """
        Converts the musicxml file into a MIDI file
        """
        sheet_music_file = converter.parse(
            "https://pub-41087431ab634ba8a456c9a62333ea39.r2.dev/Arabesque_L._66_no._1_in_E_Major.xml"
            # f"{settings.R2_PUBLIC_URL}/raw/{self.file_id}/{self.chunk_id}_{self.file_ext}"
        )  # chunk URL here
        sheet_music_file.write(fmt="midi", fp=self.temp_midi_path)

    def _create_audio(self):
        """
        Converts the MIDI file into a WAV file
        """
        fs = FluidSynth("piano.sf3")
        fs.midi_to_audio(self.temp_midi_path, self.temp_wav_path)

    def _load_midi_data(self):
        """
        Loads the MIDI data into a Numpy array
        """
        midi_data = pretty_midi.PrettyMIDI(self.temp_midi_path)

        self.midi_array = np.zeros(
            (round(midi_data.get_end_time() * FPS) + 1, 128), dtype=int
        )

        # Load the MIDI data into the array
        instrument: pretty_midi.Instrument
        for instrument in midi_data.instruments:
            # Ignore drums for now
            if not instrument.is_drum:
                note: pretty_midi.Note
                # Loop through every note
                for note in instrument.notes:
                    end = math.floor(note.end * FPS)
                    for i in range(math.ceil(note.start * FPS), end + 1):
                        self.midi_array[i][note.pitch] = end + 1 - i

    def _is_black(self, value):
        """
        Check if a pitch value is a black key or not, and return the black key value if it is, or -1 if it is a white key.
        """
        if value % 12 in BLACK_KEY_INDEXES:
            return value % 12
        return -1

    def _is_white(self, value):
        """
        Check if a pitch value is a white key and return it's index from the WHITE_KEY_INDEXES array, or -1 if not.
        """
        if value % 12 in WHITE_KEY_INDEXES:
            return WHITE_KEY_INDEXES.index(value % 12)
        return -1

    def _draw_keyboard(self, offset):
        """
        Used to draw the keyboard
        """

        # Draw keyboard background
        cv2.rectangle(
            self.canvas,
            (0, SCREEN_HEIGHT - PIANO_HEIGHT),
            (SCREEN_WIDTH, SCREEN_HEIGHT),
            (255, 255, 255),
            -1,
        )

        # Draw the white keys being pressed
        if 0 < offset <= self.midi_array.shape[0]:
            for note in range(128):
                if self.midi_array[offset - 1][note] > 0 and self._is_white(note) != -1:
                    # Determine the octave pixel position (for the image) of the note
                    octave = math.floor(note / 12) * 7 * WHITE_SIZE - 12 * WHITE_SIZE
                    x = octave + WHITE_SIZE * self._is_white(note)
                    cv2.rectangle(
                        self.canvas,
                        (x, SCREEN_HEIGHT - PIANO_HEIGHT),
                        (x + WHITE_SIZE, SCREEN_HEIGHT),
                        (250, 128, 0),
                        -1,
                    )

        # Draw key lines
        for i in range(52):
            cv2.rectangle(
                self.canvas,
                (i * WHITE_SIZE, SCREEN_HEIGHT - PIANO_HEIGHT),
                ((i + 1) * WHITE_SIZE, SCREEN_HEIGHT),
                (0, 0, 0),
                1,
            )

        # Draw the first black key
        cv2.rectangle(
            self.canvas,
            ((2 * WHITE_SIZE) - (BLACK_SIZE * 2), SCREEN_HEIGHT - PIANO_HEIGHT),
            ((2 * WHITE_SIZE) - BLACK_SIZE, round(SCREEN_HEIGHT - (PIANO_HEIGHT / 2))),
            (0, 0, 0),
            -1,
        )

        # Draw the remaining black keys
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

        # Draw the black keys being pressed
        if 0 < offset <= self.midi_array.shape[0]:
            for note in range(128):
                if self.midi_array[offset - 1][note] > 0 and self._is_black(note) != -1:
                    # Determine the octave pixel position (for the image) of the note
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
        """
        Draws the MIDI notes visible on the screen
        """

        cv2.rectangle(
            self.notes_screen,
            (0, 0),
            (self.notes_screen.shape[1], self.notes_screen.shape[0]),
            (16, 16, 16),
            -1,
        )

        for i in range(offset, offset + FRAMES_ON_SCREEN):
            # Skip the indexes out of bounds
            if i < 0 or i >= self.midi_array.shape[0]:
                continue

            for note in range(128):
                if self.midi_array[i][note] == 0:
                    continue

                # Determine the octave pixel position (for the image) of the note
                octave = math.floor(note / 12) * 7 * WHITE_SIZE - 12 * WHITE_SIZE

                # Determine if the note is on a white or black key
                if self._is_white(note) != -1:
                    # Get the X position of the white key relative to the octave position
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
        offset = (
            int(t * FPS) - FRAMES_ON_SCREEN
        )  # FRAMES_ON_SCREEN used to start the notes from the top of the video image
        self._draw_notes(offset)
        self._draw_keyboard(offset)
        return np.asarray(
            cv2.cvtColor(self.canvas, cv2.COLOR_BGR2RGB)[:, :], dtype=np.uint8
        )

    def render(self):
        self._create_midi()
        self._create_audio()
        self._load_midi_data()

        clip = VideoClip(
            self._make_frames,
            duration=(self.midi_array.shape[0] + (2 * FRAMES_ON_SCREEN)) / FPS,
        )
        audio = AudioFileClip(f"app/tmp/{self.output_file}.wav")

        clip1 = clip.subclipped(0, FRAMES_ON_SCREEN / FPS)
        clip2 = clip.subclipped(FRAMES_ON_SCREEN / FPS, clip.duration).with_audio(audio)

        final_video = concatenate_videoclips([clip1, clip2])
        final_video.write_videofile(
            f"app/tmp/{self.output_file}.mp4", fps=FPS, threads=4
        )
        for path in [
            f"app/tmp/{self.output_file}.wav",
            f"app/tmp/{self.output_file}.mid",
        ]:
            if os.path.exists(path):
                os.remove(path)
