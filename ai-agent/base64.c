#include <stddef.h>
#include <string.h>
#include <stdio.h>

int b64_lookup(char c) { // function converts chars to correspodning b64 vals
    if (c >= 'A' && c <= 'Z') return c - 'A';
    if (c >= 'a' && c <= 'z') return c - 'a' + 26;
    if (c >= '0' && c <= '9') return c- '0' + 52;
    if (c == '-') return 62;
    if (c == '_') return 63;
    return -1;
};

void b64_decode(const char *in, unsigned char *out, size_t *out_len) {
    *out_len = 0; // init out_len
    while(in[0] != '\0') { // while in is not null term
        // get first 4 (v1, v2, v3, v4) chars and return their corresponding b64 vals
        int v1 = b64_lookup(in[0]); 
        int v2 = b64_lookup(in[1]);
        int v3 = b64_lookup(in[2]);
        int v4 = b64_lookup(in[3]);

        out[0] = (v1 << 2) | (v2 >> 4); // since v1 outputs 6 bits, we move the 6 bits of v1 to the left to make room for first 2 of v2. v2 shift is 4, first 2 vals get shifted into v1, last 4 make room for 4 more on end
        *out_len += 1; // increase outlen by 1 byte

        if (in[2] == '\0' || in[2] == '=') break; // check to see if message ended
        out[1] = (v2 << 4) | (v3 >> 2); // second out byte is last 4 digs of v2, and first 4 of v3.
        *out_len += 1;// increase outlen by 1 byte

        if (in[3] == '\0' || in[3] == '=') break; // check to see if msg ended
        out[2] = (v3 << 6) | v4; // last byte is last 2 of v3, and all 6 of v4
        *out_len += 1;// increase outlen by 1 byte

        out += 3; // first 4 chars packed into 3 bytes
        in += 4; // first 4 chars completed
    }
};
// IGNORE TEST CASES
#ifdef TEST
int main(void) {
    unsigned char out[64]; // max 64 bytes just for testing
    size_t out_len; // initialize out_len, function assigns this a value

    b64_decode("SGVsbG8=", out, &out_len); // "Hello"
    printf("%.*s\n", (int)out_len, out);

    b64_decode("dGVzdA", out, &out_len); // "test"
    printf("%.*s\n", (int)out_len, out);


    return 0;
}
#endif