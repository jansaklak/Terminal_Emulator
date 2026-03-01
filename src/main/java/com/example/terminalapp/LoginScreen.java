package com.example.terminalapp;

import javafx.application.Platform;
import javafx.collections.FXCollections;
import javafx.geometry.Insets;
import javafx.geometry.Pos;
import javafx.scene.Scene;
import javafx.scene.control.*;
import javafx.scene.layout.GridPane;
import javafx.scene.layout.HBox;
import javafx.scene.paint.Color;
import javafx.scene.text.Font;
import javafx.scene.text.FontWeight;
import javafx.scene.text.Text;
import javafx.stage.Stage;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.net.Socket;
import java.nio.charset.StandardCharsets;

/**
 * Okno logowania.
 *
 * Użytkownik podaje numeryczny kod dostępu i wybiera konfigurację.
 * Po kliknięciu "Połącz" klient:
 *   1. Otwiera gniazdo TCP do serwera.
 *   2. Wysyła handshake JSON: {"code":"...", "config":"..."}
 *   3. Odczytuje odpowiedź JSON z serwera.
 *   4. W przypadku sukcesu otwiera okno terminala; w razie błędu wyświetla komunikat.
 */
public class LoginScreen {

    private static final String DEFAULT_HOST = "127.0.0.1";
    private static final int    DEFAULT_PORT = 5000;

    private final Stage      primaryStage;
    private final TerminalApp terminalApp;

    public LoginScreen(Stage primaryStage, TerminalApp terminalApp) {
        this.primaryStage = primaryStage;
        this.terminalApp  = terminalApp;
    }

    public void show() {
        primaryStage.setTitle("Terminal – logowanie");

        // Layout
        GridPane grid = new GridPane();
        grid.setAlignment(Pos.CENTER);
        grid.setHgap(10);
        grid.setVgap(10);
        grid.setPadding(new Insets(30));
        grid.setStyle("-fx-background-color: #1e1e2e;");

        Text title = new Text("Połącz z serwerem");
        title.setFont(Font.font("Consolas", FontWeight.BOLD, 22));
        title.setFill(Color.web("#cdd6f4"));
        grid.add(title, 0, 0, 2, 1);

        // Host serwera
        Label hostLabel = new Label("Serwer:");
        hostLabel.setTextFill(Color.web("#a6adc8"));
        grid.add(hostLabel, 0, 1);
        TextField hostField = new TextField(DEFAULT_HOST);
        hostField.setStyle("-fx-background-color: #313244; -fx-text-fill: #cdd6f4;");
        grid.add(hostField, 1, 1);

        // Port serwera
        Label portLabel = new Label("Port:");
        portLabel.setTextFill(Color.web("#a6adc8"));
        grid.add(portLabel, 0, 2);
        TextField portField = new TextField(String.valueOf(DEFAULT_PORT));
        portField.setStyle("-fx-background-color: #313244; -fx-text-fill: #cdd6f4;");
        grid.add(portField, 1, 2);

        // Kod dostępu
        Label codeLabel = new Label("Kod dostępu:");
        codeLabel.setTextFill(Color.web("#a6adc8"));
        grid.add(codeLabel, 0, 3);
        PasswordField codeField = new PasswordField();
        codeField.setPromptText("np. 1234");
        codeField.setStyle("-fx-background-color: #313244; -fx-text-fill: #cdd6f4; -fx-prompt-text-fill: #585b70;");
        grid.add(codeField, 1, 3);

        // Konfiguracja
        Label cfgLabel = new Label("Konfiguracja:");
        cfgLabel.setTextFill(Color.web("#a6adc8"));
        grid.add(cfgLabel, 0, 4);
        ComboBox<String> cfgBox = new ComboBox<>(FXCollections.observableArrayList(
                "Bazy1", "BazyRoot", "ResetDatabase", "LinuxTerminal"
        ));
        cfgBox.getSelectionModel().selectFirst();
        cfgBox.setStyle("-fx-background-color: #313244; -fx-text-fill: #cdd6f4; -fx-prompt-text-fill: #cdd6f4;");
        cfgBox.setButtonCell(new ListCell<String>() {
            @Override
            protected void updateItem(String item, boolean empty) {
                super.updateItem(item, empty);
                if (empty || item == null) {
                    setText(null);
                } else {
                    setText(item);
                    setTextFill(Color.web("#cdd6f4"));
                }
            }
        });
        grid.add(cfgBox, 1, 4);

        // Przycisk połączenia
        Button connectBtn = new Button("Połącz");
        connectBtn.setStyle(
                "-fx-background-color: #89b4fa; -fx-text-fill: #1e1e2e; " +
                        "-fx-font-weight: bold; -fx-cursor: hand;");
        HBox btnBox = new HBox(connectBtn);
        btnBox.setAlignment(Pos.BOTTOM_RIGHT);
        grid.add(btnBox, 1, 5);

        // Komunikat statusu
        Text statusText = new Text();
        statusText.setFont(Font.font("Consolas", 12));
        grid.add(statusText, 0, 6, 2, 1);

        // Akcja połączenia
        Runnable doConnect = () -> {
            String host   = hostField.getText().trim();
            String portStr = portField.getText().trim();
            String code   = codeField.getText().trim();
            String config = cfgBox.getValue();

            int port;
            try {
                port = Integer.parseInt(portStr);
            } catch (NumberFormatException e) {
                statusText.setFill(Color.web("#f38ba8"));
                statusText.setText("Nieprawidłowy port.");
                return;
            }

            if (code.isEmpty()) {
                statusText.setFill(Color.web("#f38ba8"));
                statusText.setText("Podaj kod dostępu.");
                return;
            }

            connectBtn.setDisable(true);
            statusText.setFill(Color.web("#fab387"));
            statusText.setText("Łączenie z " + host + ":" + port + " …");

            // Operacje sieciowe poza wątkiem FX
            Thread thread = new Thread(() -> {
                try {
                    Socket socket = new Socket(host, port);

                    // Wysłanie handshake
                    JSONObject req = new JSONObject();
                    req.put("code",   code);
                    req.put("config", config);
                    PrintWriter pw = new PrintWriter(
                            new OutputStreamWriter(socket.getOutputStream(), StandardCharsets.UTF_8), true);
                    pw.println(req.toString());

                    // Odczyt odpowiedzi (pojedyncza linia JSON)
                    BufferedReader br = new BufferedReader(
                            new InputStreamReader(socket.getInputStream(), StandardCharsets.UTF_8));
                    String line = br.readLine();
                    JSONObject resp = new JSONObject(line);

                    if (!resp.optBoolean("ok", false)) {
                        String error = resp.optString("error", "Błąd autoryzacji");
                        Platform.runLater(() -> {
                            statusText.setFill(Color.web("#f38ba8"));
                            statusText.setText("✗ " + error);
                            connectBtn.setDisable(false);
                        });
                        socket.close();
                        return;
                    }

                    String username = resp.optString("username", code);

                    // Autoryzacja OK – otwarcie terminala
                    SocketTtyConnector connector = new SocketTtyConnector(socket);
                    Platform.runLater(() -> {
                        try {
                            Stage termStage = new Stage();
                            terminalApp.showTerminal(termStage, username, connector);
                            primaryStage.close();
                        } catch (Exception ex) {
                            statusText.setFill(Color.web("#f38ba8"));
                            statusText.setText("Błąd otwierania terminala: " + ex.getMessage());
                            connectBtn.setDisable(false);
                        }
                    });

                } catch (Exception ex) {
                    Platform.runLater(() -> {
                        statusText.setFill(Color.web("#f38ba8"));
                        statusText.setText("Błąd połączenia: " + ex.getMessage());
                        connectBtn.setDisable(false);
                    });
                }
            }, "connect-thread");
            thread.setDaemon(true);
            thread.start();
        };

        connectBtn.setOnAction(e -> doConnect.run());
        // Obsługa klawisza Enter w polu kodu
        codeField.setOnAction(e -> doConnect.run());

        Scene scene = new Scene(grid, 420, 340);
        primaryStage.setScene(scene);
        primaryStage.show();
    }
}
