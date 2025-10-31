bin := latlon

CC = gcc

CFLAGS += -Wall
CFLAGS += -Wextra
CFLAGS += -Wpedantic
CFLAGS += -std=c23
CFLAGS += -O3

LDFLAGS += -lm

PREFIX ?= $(HOME)/.local/share/dzgui

all: $(bin)

install: $(bin)
	install -Dm 755 $(bin) $(PREFIX)

$(bin): latlon.c
	$(CC) $(CFLAGS) $^ -o $@ $(LDFLAGS)

clean:
	rm -f $(bin)
