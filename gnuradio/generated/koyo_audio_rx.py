#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: KOYO SatNOGS Audio RX
# Author: KOYO project
# Description: KOYO audio RX
# GNU Radio version: 3.10.12.0

from gnuradio import blocks
from gnuradio import blocks, gr
from gnuradio import gr
from gnuradio.filter import firdes
from gnuradio.fft import window
import sys
import signal
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
import satellites.components.datasinks
import satellites.components.deframers
import satellites.components.demodulators
import threading




class koyo_audio_rx(gr.top_block):

    def __init__(self):
        gr.top_block.__init__(self, "KOYO SatNOGS Audio RX", catch_exceptions=True)
        self.flowgraph_started = threading.Event()

        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate = 48000
        self.kiss_file = kiss_file = r'data/koyo/observations/14526577/grc_output.kiss'
        self.baudrate = baudrate = 9600
        self.audio_file = audio_file = r'data/koyo/observations/14526577/obs_14526577.wav'

        ##################################################
        # Blocks
        ##################################################

        self.satellites_kiss_file_sink_0 = satellites.components.datasinks.kiss_file_sink(kiss_file, append = False, options="")
        self.satellites_fsk_demodulator_0 = satellites.components.demodulators.fsk_demodulator(baudrate = baudrate, samp_rate = samp_rate, iq = False, subaudio = False, options="--clk_bw 0.15")
        self.satellites_ax25_deframer_0 = satellites.components.deframers.ax25_deframer(g3ruh_scrambler=True, options="")
        self.blocks_wavfile_source_0 = blocks.wavfile_source(audio_file, False)
        self.blocks_message_debug_0 = blocks.message_debug(True, gr.log_levels.info)


        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.satellites_ax25_deframer_0, 'out'), (self.blocks_message_debug_0, 'print_pdu'))
        self.msg_connect((self.satellites_ax25_deframer_0, 'out'), (self.satellites_kiss_file_sink_0, 'in'))
        self.connect((self.blocks_wavfile_source_0, 0), (self.satellites_fsk_demodulator_0, 0))
        self.connect((self.satellites_fsk_demodulator_0, 0), (self.satellites_ax25_deframer_0, 0))


    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate

    def get_kiss_file(self):
        return self.kiss_file

    def set_kiss_file(self, kiss_file):
        self.kiss_file = kiss_file

    def get_baudrate(self):
        return self.baudrate

    def set_baudrate(self, baudrate):
        self.baudrate = baudrate

    def get_audio_file(self):
        return self.audio_file

    def set_audio_file(self, audio_file):
        self.audio_file = audio_file




def main(top_block_cls=koyo_audio_rx, options=None):
    tb = top_block_cls()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    tb.start()
    tb.flowgraph_started.set()

    tb.wait()


if __name__ == '__main__':
    main()
