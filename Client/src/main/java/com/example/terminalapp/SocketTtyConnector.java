package com.example.terminalapp;

import com.jediterm.terminal.TtyConnector;
import org.json.JSONObject;

import java.io.*;
import java.net.Socket;
import java.nio.charset.StandardCharsets;

/**
 * Łączy bibliotekę JediTerm z serwerem bramy TCP (Python).
 * Zoptymalizowana pod kątem stabilności i braku blokowania wątków.
 */
public class SocketTtyConnector implements TtyConnector {

    private static final String RESET_CONTROL = "{\"__control__\":\"reset_session\"}\n";
    private static final String CLEAR_CONTROL = "{\"__control__\":\"clear_screen\"}\n";
    private static final String GET_CMDS_CONTROL = "{\"__control__\":\"get_commands\"}\n";

    private final Socket socket;
    private final OutputStream out;
    private final InputStreamReader reader;
    private volatile boolean closed = false;

    private String lastCommandsData = null;
    private final Object commandsLock = new Object();
    private final Object bufferLock = new Object();
    
    // Bufor wewnętrzny do filtrowania danych
    private final StringBuilder internalBuffer = new StringBuilder();

    public SocketTtyConnector(Socket socket) throws IOException {
        this.socket = socket;
        this.out = socket.getOutputStream();
        this.reader = new InputStreamReader(socket.getInputStream(), StandardCharsets.UTF_8);
    }

    @Override
    public int read(char[] buf, int offset, int length) throws IOException {
        while (true) {
            synchronized (bufferLock) {
                // 1. Sprawdź czy mamy kompletny JSON w buforze
                int startIdx = internalBuffer.indexOf("{\"__control__\"");
                if (startIdx != -1) {
                    // Jeśli przed JSONem są dane terminalowe, zwróć je najpierw!
                    if (startIdx > 0) {
                        int toCopy = Math.min(length, startIdx);
                        internalBuffer.getChars(0, toCopy, buf, offset);
                        internalBuffer.delete(0, toCopy);
                        return toCopy;
                    }

                    // JSON jest na początku bufora. Szukaj końca linii.
                    int newLineIdx = internalBuffer.indexOf("\n", startIdx);
                    if (newLineIdx != -1) {
                        // Mamy pełną linię z JSONem
                        String line = internalBuffer.substring(startIdx, newLineIdx).trim();
                        processControlMessage(line);
                        internalBuffer.delete(startIdx, newLineIdx + 1);
                        // Po przetworzeniu JSONa, kontynuuj pętlę while, aby sprawdzić co zostało
                        continue;
                    }
                    // JSON jest niekompletny na początku bufora -> musimy doczytać z sieci (niżej)
                } else {
                    // Brak JSONa. Jeśli są jakiekolwiek dane, zwróć je.
                    if (internalBuffer.length() > 0) {
                        // Zabezpieczenie przed ucięciem markera na końcu (jeśli bufor kończy się na '{')
                        int lastBrace = internalBuffer.lastIndexOf("{");
                        int toCopy = internalBuffer.length();
                        if (lastBrace != -1 && lastBrace > internalBuffer.length() - 15) {
                            if ("{\"__control__\"".startsWith(internalBuffer.substring(lastBrace))) {
                                toCopy = lastBrace;
                            }
                        }

                        if (toCopy > 0) {
                            int actualToCopy = Math.min(length, toCopy);
                            internalBuffer.getChars(0, actualToCopy, buf, offset);
                            internalBuffer.delete(0, actualToCopy);
                            return actualToCopy;
                        }
                        // Jeśli toCopy == 0, bo mamy tylko "{" na końcu, musimy doczytać.
                    }
                }
            }

            // Jeśli doszliśmy tutaj, znaczy że bufor jest pusty lub ma tylko niekompletny JSON.
            // Wykonaj blokujący odczyt z sieci.
            char[] temp = new char[8192];
            int n = reader.read(temp);
            if (n <= 0) return n;
            
            synchronized (bufferLock) {
                internalBuffer.append(temp, 0, n);
            }
            // Pętla while spróbuje teraz przetworzyć nowo przybyłe dane.
        }
    }

    private void processControlMessage(String line) {
        try {
            JSONObject json = new JSONObject(line);
            if ("commands_data".equals(json.optString("__control__"))) {
                synchronized (commandsLock) {
                    try {
                        if (json.optBoolean("b64", false)) {
                            byte[] decoded = java.util.Base64.getDecoder().decode(json.optString("data", ""));
                            lastCommandsData = new String(decoded, StandardCharsets.UTF_8);
                        } else {
                            lastCommandsData = json.optString("data", "");
                        }
                    } catch (Exception e) {
                        e.printStackTrace();
                        lastCommandsData = "";
                    }
                    commandsLock.notifyAll();
                }
            }
        } catch (Exception e) {
            // To nie był poprawny JSON kontrolny, zignoruj (zostanie usunięty z bufora)
            e.printStackTrace();
        }
    }

    public String getRecordedCommandsText() {
        synchronized (commandsLock) {
            lastCommandsData = null;
            try {
                write(GET_CMDS_CONTROL);
                // Czekamy na przechwycenie odpowiedzi w metodzie read()
                commandsLock.wait(5000);
            } catch (Exception e) {
                e.printStackTrace();
            }
            return lastCommandsData != null ? lastCommandsData : "";
        }
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

    public void requestReset() throws IOException {
        write(RESET_CONTROL);
    }

    public void requestClear() throws IOException {
        write(CLEAR_CONTROL);
    }

    public void requestLoadCommands(byte[] fileData) throws IOException {
        JSONObject payload = new JSONObject();
        payload.put("__control__", "load_commands");
        String b64 = java.util.Base64.getEncoder().encodeToString(fileData);
        payload.put("data", b64);
        payload.put("b64", true);
        payload.put("execute", true);
        write(payload.toString() + "\n");
    }

    public void requestAppendCommand(String command) throws IOException {
        JSONObject payload = new JSONObject();
        payload.put("__control__", "append_command");
        payload.put("command", command);
        write(payload.toString() + "\n");
    }

    @Override
    public boolean isConnected() {
        return !closed && socket.isConnected() && !socket.isClosed();
    }

    @Override
    public int waitFor() throws InterruptedException {
        while (isConnected()) {
            Thread.sleep(200);
        }
        return 0;
    }

    @Override
    public boolean ready() throws IOException {
        synchronized (bufferLock) {
            return internalBuffer.length() > 0 || reader.ready();
        }
    }

    @Override
    public void close() {
        if (closed) return;
        closed = true;
        try { socket.close(); } catch (IOException ignored) {}
    }

    @Override
    public String getName() {
        return "Terminal Gateway";
    }
}
