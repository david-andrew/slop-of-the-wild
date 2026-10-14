/* LD_PRELOAD guard for CPU-only builders. An attempted graphics/window load
 * aborts rather than allowing a software fallback to hide the dependency. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

void *dlopen(const char *filename, int flags) {
    static void *(*real_dlopen)(const char *, int);
    const char *blocked[] = {
        "libGL", "libEGL", "libOpenGL", "libvulkan", "libX11", "libxcb",
        "libwayland", "libSDL", "libglfw", "libgbm", "libdrm"
    };
    if (filename) {
        const char *name = strrchr(filename, '/');
        name = name ? name + 1 : filename;
        for (size_t i = 0; i < sizeof(blocked) / sizeof(blocked[0]); ++i) {
            if (strncmp(name, blocked[i], strlen(blocked[i])) == 0) {
                fprintf(stderr, "CPU-only guard: attempted graphics/window load: %s\n", filename);
                _exit(86);
            }
        }
    }
    if (!real_dlopen) real_dlopen = dlsym(RTLD_NEXT, "dlopen");
    return real_dlopen(filename, flags);
}
