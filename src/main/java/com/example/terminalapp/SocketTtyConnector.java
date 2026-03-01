package com.example.terminalapp;

import com.jediterm.terminal.TtyConnector;

import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.Socket;
import java.nio.charset.StandardCharsets;

/**
 * Łączy bibliotekę JediTerm z serwerem bramy TCP (Python).
 * Handshake (JSON) jest wykonywany przed utworzeniem tego konektora.
 * Wywołujący przekazuje już uwierzytelnione gniazdo, aby ta klasa pozostała prosta.
 */
public class SocketTtyConnector implements TtyConnector {

    private final Socket socket;
    private final InputStreamReader reader;
    private final OutputStream out;
    private volatile boolean closed = false;

    /**
     * @param socket Już połączone i uwierzytelnione gniazdo.
     */
    public SocketTtyConnector(Socket socket) throws IOException {
        this.socket = socket;
        this.reader = new InputStreamReader(socket.getInputStream(), StandardCharsets.UTF_8);
        this.out = socket.getOutputStream();
    }

    // ── Interfejs TtyConnector ────────────────────────────────────────────

    @Override
    public int read(char[] buf, int offset, int length) throws IOException {
        return reader.read(buf, offset, length);
    }

    @Override
    public void write(String string) throws IOException {
        out.write(string.getBytes(StandardCharsets.UTF_8));
        out.flush();
    }

    @Override
    public void write(byte[] bytes) throws IOException {
        out.write(bytes);
        out.flush();
    }

    @Override
    public boolean isConnected() {
        return !closed && socket.isConnected() && !socket.isClosed();
    }

    @Override
    public int waitFor() throws InterruptedException {
        // Blokuje do momentu zamknięcia gniazda
        while (isConnected()) {
            Thread.sleep(200);
        }
        return 0;
    }

    @Override
    public boolean ready() throws IOException {
        return reader.ready();
    }

    @Override
    public void close() {
        closed = true;
        try { socket.close(); } catch (IOException ignored) {}
    }

    @Override
    public String getName() {
        return "Terminal Gateway";
    }
}
