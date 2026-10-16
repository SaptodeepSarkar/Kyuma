/* CleanMic DSP: real RNNoise suppressor + brickwall limiter (LADSPA).
 * Built from scratch against librnnoise (present on system) — no downloads.
 * Two mono plugins in one .so:
 *   cleanmic_rnnoise  — VAD-gated RNNoise suppression
 *   cleanmic_limiter  — peak limiter, instant attack, 50ms release
 */
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include <rnnoise.h>

/* ---- minimal LADSPA header (stable ABI, v1.1) ---- */
typedef float LADSPA_Data;
typedef void *LADSPA_Handle;
typedef int LADSPA_PortDescriptor;
typedef struct _LADSPA_PortRangeHint {
    unsigned long HintDescriptor;
    LADSPA_Data LowerBound, UpperBound;
} LADSPA_PortRangeHint;
typedef struct _LADSPA_Descriptor {
    unsigned long UniqueID;
    const char *Label;
    unsigned long Properties;
    const char *Name, *Maker, *Copyright;
    unsigned long PortCount;
    const LADSPA_PortDescriptor *PortDescriptors;
    const char *const *PortNames;
    const LADSPA_PortRangeHint *PortRangeHints;
    void *ImplementationData;
    LADSPA_Handle (*instantiate)(const struct _LADSPA_Descriptor *, unsigned long);
    void (*connect_port)(LADSPA_Handle, unsigned long, LADSPA_Data *);
    void (*activate)(LADSPA_Handle);
    void (*run)(LADSPA_Handle, unsigned long);
    void (*run_adding)(LADSPA_Handle, unsigned long, LADSPA_Data, LADSPA_Data);
    void (*set_run_adding_gain)(LADSPA_Handle, LADSPA_Data);
    void (*deactivate)(LADSPA_Handle);
    void (*cleanup)(LADSPA_Handle);
} LADSPA_Descriptor;
#define LADSPA_PORT_INPUT 0x1
#define LADSPA_PORT_OUTPUT 0x2
#define LADSPA_PORT_AUDIO 0x4
#define LADSPA_PORT_CONTROL 0x8
#define LADSPA_HINT_BOUNDED_BELOW 0x1
#define LADSPA_HINT_BOUNDED_ABOVE 0x2
#define LADSPA_HINT_DEFAULT_0 0x10
#define LADSPA_HINT_DEFAULT_1 0x40
#define LADSPA_HINT_DEFAULT_50 0xC0
#define LADSPA_PROPERTY_HARD_RT_CAPABLE 0x1

/* ---- rnnoise suppressor ---- */
#define RN_FRAME 480
typedef struct {
    DenoiseState *st;
    LADSPA_Data *in, *out, *vad_thr;
    float buf[RN_FRAME];
    float fifo[4096]; /* latency line; produced/emitted counters, never negative */
    int fill, fifo_w, fifo_r;
    long produced, emitted;
} RNInst;

static LADSPA_Handle rn_inst(const LADSPA_Descriptor *d, unsigned long rate) {
    (void)d; (void)rate;
    RNInst *s = calloc(1, sizeof *s);
    if (s) s->st = rnnoise_create(NULL);
    return s;
}
static void rn_connect(LADSPA_Handle h, unsigned long p, LADSPA_Data *d) {
    RNInst *s = h;
    if (p == 0) s->in = d; else if (p == 1) s->out = d; else s->vad_thr = d;
}
static void rn_run(LADSPA_Handle h, unsigned long n) {
    RNInst *s = h;
    float thr = s->vad_thr ? *s->vad_thr : 50.0f;
    for (unsigned long i = 0; i < n; i++) {
        s->buf[s->fill++] = s->in[i];
        if (s->fill == RN_FRAME) {
            float denoised[RN_FRAME];
            float vad = rnnoise_process_frame(s->st, denoised, s->buf);
            float gate = (vad * 100.0f >= thr) ? 1.0f : 0.001f; /* -60dB, no voice */
            for (int j = 0; j < RN_FRAME; j++) {
                s->fifo[s->fifo_w] = denoised[j] * gate;
                s->fifo_w = (s->fifo_w + 1) % 4096;
                s->produced++;
            }
            s->fill = 0;
        }
        /* constant 10ms latency: emit only samples 480+ old */
        if (s->produced - s->emitted > RN_FRAME) {
            s->out[i] = s->fifo[s->fifo_r];
            s->fifo_r = (s->fifo_r + 1) % 4096;
            s->emitted++;
        } else {
            s->out[i] = 0.0f;
        }
    }
}
static void rn_cleanup(LADSPA_Handle h) {
    RNInst *s = h;
    rnnoise_destroy(s->st);
    free(s);
}
static const LADSPA_PortDescriptor rn_ports[] = {
    LADSPA_PORT_INPUT | LADSPA_PORT_AUDIO,
    LADSPA_PORT_OUTPUT | LADSPA_PORT_AUDIO,
    LADSPA_PORT_INPUT | LADSPA_PORT_CONTROL,
};
static const char *const rn_names[] = {"Input", "Output", "vad_threshold"};
static const LADSPA_PortRangeHint rn_hints[] = {
    {0, 0, 0},
    {0, 0, 0},
    {LADSPA_HINT_BOUNDED_BELOW | LADSPA_HINT_BOUNDED_ABOVE | LADSPA_HINT_DEFAULT_50, 0, 100},
};
static const LADSPA_Descriptor rn_desc = {
    9000101, "cleanmic_rnnoise", LADSPA_PROPERTY_HARD_RT_CAPABLE,
    "CleanMic RNNoise", "Kyuma", "MIT", 3, rn_ports, rn_names, rn_hints, NULL,
    rn_inst, rn_connect, NULL, rn_run, NULL, NULL, NULL, rn_cleanup,
};

/* ---- brickwall limiter ---- */
typedef struct {
    LADSPA_Data *in, *out, *thresh_db;
    float peak; /* envelope follower */
} LimInst;
static LADSPA_Handle lim_inst(const LADSPA_Descriptor *d, unsigned long rate) {
    (void)d; (void)rate;
    LimInst *s = calloc(1, sizeof *s);
    return s;
}
static void lim_connect(LADSPA_Handle h, unsigned long p, LADSPA_Data *d) {
    LimInst *s = h;
    if (p == 0) s->in = d; else if (p == 1) s->out = d; else s->thresh_db = d;
}
static void lim_run(LADSPA_Handle h, unsigned long n) {
    LimInst *s = h;
    /* 50ms release at 48k: coeff per sample */
    const float rel = expf(-1.0f / (0.05f * 48000.0f));
    float ceil_lin = powf(10.0f, (s->thresh_db ? *s->thresh_db : -3.0f) / 20.0f);
    for (unsigned long i = 0; i < n; i++) {
        float a = fabsf(s->in[i]);
        if (a > s->peak) s->peak = a;            /* instant attack */
        else s->peak += (a - s->peak) * (1 - rel); /* smooth release */
        float g = (s->peak > ceil_lin) ? ceil_lin / s->peak : 1.0f;
        s->out[i] = s->in[i] * g;
    }
}
static void lim_cleanup(LADSPA_Handle h) { free(h); }
static const LADSPA_PortDescriptor lim_ports[] = {
    LADSPA_PORT_INPUT | LADSPA_PORT_AUDIO,
    LADSPA_PORT_OUTPUT | LADSPA_PORT_AUDIO,
    LADSPA_PORT_INPUT | LADSPA_PORT_CONTROL,
};
static const char *const lim_names[] = {"Input", "Output", "ceiling_db"};
static const LADSPA_PortRangeHint lim_hints[] = {
    {0, 0, 0},
    {0, 0, 0},
    {LADSPA_HINT_BOUNDED_BELOW | LADSPA_HINT_BOUNDED_ABOVE | LADSPA_HINT_DEFAULT_0, -24, 0},
};
static const LADSPA_Descriptor lim_desc = {
    9000102, "cleanmic_limiter", LADSPA_PROPERTY_HARD_RT_CAPABLE,
    "CleanMic Limiter", "Kyuma", "MIT", 3, lim_ports, lim_names, lim_hints, NULL,
    lim_inst, lim_connect, NULL, lim_run, NULL, NULL, NULL, lim_cleanup,
};

const LADSPA_Descriptor *ladspa_descriptor(unsigned long i) {
    if (i == 0) return &rn_desc;
    if (i == 1) return &lim_desc;
    return NULL;
}
