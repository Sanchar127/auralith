import soundfile as sf
import pyloudnorm as pyln


from pedalboard import (
    Pedalboard,
    Compressor,
    Limiter,
    Gain,
    HighpassFilter,
    LowShelfFilter,
    HighShelfFilter
)



from config import TARGET_LUFS



def master_audio(
    input_file,
    output_file
):


    audio, sr = sf.read(
        input_file
    )


    # convert stereo format
    if audio.ndim == 1:
        audio = audio.reshape(
            -1,
            1
        )


    # -------------------------
    # DSP MASTERING
    # -------------------------

    board = Pedalboard(
        [

            HighpassFilter(
                cutoff_frequency=30
            ),


            LowShelfFilter(
                cutoff_frequency=120,
                gain_db=2
            ),


            HighShelfFilter(
                cutoff_frequency=8000,
                gain_db=1
            ),


            Compressor(
                threshold_db=-18,
                ratio=3,
                attack_ms=10,
                release_ms=100
            ),


            Gain(
                gain_db=2
            ),


            Limiter(
                threshold_db=-1
            )

        ]
    )


    processed = board(
        audio.T,
        sr
    )


    processed = processed.T



    # -------------------------
    # LOUDNESS NORMALIZATION
    # -------------------------

    meter = pyln.Meter(
        sr
    )


    loudness = meter.integrated_loudness(
        processed
    )


    processed = pyln.normalize.loudness(
        processed,
        loudness,
        TARGET_LUFS
    )


    sf.write(
        output_file,
        processed,
        sr
    )


    return output_file