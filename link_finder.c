#define _CRT_SECURE_NO_WARNINGS
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <windows.h>

static int extract_url(const char *line, char *out, size_t out_size) {
    const char *start = strstr(line, "https://");
    if (!start) return 0;

    const char *end = strstr(start, ".trycloudflare.com");
    if (!end) return 0;
    end += strlen(".trycloudflare.com");

    size_t len = (size_t)(end - start);
    if (len == 0 || len >= out_size) return 0;

    memcpy(out, start, len);
    out[len] = '\0';
    return 1;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "Usage: link_finder.exe RUN_ID [TIMEOUT_SECONDS]\n");
        return 2;
    }

    const char *run_id = argv[1];
    int timeout_seconds = (argc >= 3) ? atoi(argv[2]) : 180;
    if (timeout_seconds < 1) timeout_seconds = 180;

    char command[512];
    char line[8192];
    char found_url[512];
    DWORD started = GetTickCount();

    snprintf(command, sizeof(command),
        "gh run view %s --repo Parsa0369/crypto --log 2>NUL", run_id);

    while ((DWORD)(GetTickCount() - started) < (DWORD)timeout_seconds * 1000UL) {
        FILE *pipe = _popen(command, "r");
        if (pipe) {
            while (fgets(line, sizeof(line), pipe)) {
                if (extract_url(line, found_url, sizeof(found_url))) {
                    // Drain the command output so the child process can exit cleanly.
                    while (fgets(line, sizeof(line), pipe)) { }
                    _pclose(pipe);
                    puts(found_url);
                    return 0;
                }
            }
            _pclose(pipe);
        }

        Sleep(1500);
    }

    return 1;
}
