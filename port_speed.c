/* CryptoPulse localhost port scanner: scans 1000-9999, preferring 8080.
   Checks local port availability, not Internet speed.
   Windows MinGW: gcc port_speed.c -o port_speed.exe -lws2_32
   Linux/macOS: cc port_speed.c -o port_speed
*/
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <winsock2.h>
#include <ws2tcpip.h>
#include <stdio.h>
typedef SOCKET socket_t;
#define CLOSESOCKET closesocket
#define INVALID_SOCKET_VALUE INVALID_SOCKET
#else
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>
#include <stdio.h>
typedef int socket_t;
#define CLOSESOCKET close
#define INVALID_SOCKET_VALUE (-1)
#endif

static int can_bind_port(int port) {
    socket_t s = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (s == INVALID_SOCKET_VALUE) return 0;
    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_port = htons((unsigned short)port);
    addr.sin_addr.s_addr = htonl(0x7f000001UL);
    int ok = bind(s, (struct sockaddr *)&addr, (int)sizeof(addr)) == 0;
    CLOSESOCKET(s);
    return ok;
}

int main(void) {
#ifdef _WIN32
    WSADATA data;
    if (WSAStartup(MAKEWORD(2, 2), &data) != 0) {
        fprintf(stderr, "Winsock initialization failed.\n");
        return 2;
    }
#endif
    int selected = 0;
    if (can_bind_port(8080)) selected = 8080;
    else {
        for (int p = 1000; p <= 9999; ++p) {
            if (p != 8080 && can_bind_port(p)) { selected = p; break; }
        }
    }
    if (selected) printf("%d\n", selected);
    else fprintf(stderr, "No available port found in range 1000-9999.\n");
#ifdef _WIN32
    WSACleanup();
#endif
    return selected ? 0 : 1;
}
