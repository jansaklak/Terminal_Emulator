package com.example.terminalapp;

import javafx.application.Platform;
import javafx.geometry.Insets;
import javafx.geometry.Pos;
import javafx.scene.Scene;
import javafx.scene.control.*;
import javafx.scene.layout.GridPane;
import javafx.scene.layout.HBox;
import javafx.scene.layout.VBox;
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
 * Proces:
 * 1. Użytkownik podaje dane serwera, login i hasło.
 * 2. Po kliknięciu "Połącz", klient wysyła dane do serwera.
 * 3. Jeśli dane są poprawne, serwer odsyła listę dostępnych konfiguracji.
 * 4. UI zmienia się dynamicznie na listę przycisków wyboru środowiska.
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

        // Host
        Label hostLabel = new Label("Serwer:");
        hostLabel.setTextFill(Color.web("#a6adc8"));
        grid.add(hostLabel, 0, 1);
        TextField hostField = new TextField(DEFAULT_HOST);
        hostField.setStyle("-fx-background-color: #313244; -fx-text-fill: #cdd6f4;");
        grid.add(hostField, 1, 1);

        // Port
        Label portLabel = new Label("Port:");
        portLabel.setTextFill(Color.web("#a6adc8"));
        grid.add(portLabel, 0, 2);
        TextField portField = new TextField(String.valueOf(DEFAULT_PORT));
        portField.setStyle("-fx-background-color: #313244; -fx-text-fill: #cdd6f4;");
        grid.add(portField, 1, 2);

        // Login
        Label loginLabel = new Label("Login:");
        loginLabel.setTextFill(Color.web("#a6adc8"));
        grid.add(loginLabel, 0, 3);
        TextField loginField = new TextField();
        loginField.setPromptText("użytkownik");
        loginField.setStyle("-fx-background-color: #313244; -fx-text-fill: #cdd6f4; -fx-prompt-text-fill: #585b70;");
        grid.add(loginField, 1, 3);

        // Hasło
        Label passwordLabel = new Label("Hasło:");
        passwordLabel.setTextFill(Color.web("#a6adc8"));
        grid.add(passwordLabel, 0, 4);
        PasswordField passwordField = new PasswordField();
        passwordField.setPromptText("hasło");
        passwordField.setStyle("-fx-background-color: #313244; -fx-text-fill: #cdd6f4; -fx-prompt-text-fill: #585b70;");
        grid.add(passwordField, 1, 4);

        // Przycisk
        Button connectBtn = new Button("Zaloguj");
        connectBtn.setStyle("-fx-background-color: #89b4fa; -fx-text-fill: #1e1e2e; -fx-font-weight: bold; -fx-cursor: hand;");
        HBox btnBox = new HBox(connectBtn);
        btnBox.setAlignment(Pos.BOTTOM_RIGHT);
        grid.add(btnBox, 1, 5);

        Text statusText = new Text();
        statusText.setFont(Font.font("Consolas", 12));
        grid.add(statusText, 0, 6, 2, 1);

        Runnable doConnect = () -> {
            String host = hostField.getText().trim();
            String portStr = portField.getText().trim();
            String login = loginField.getText().trim();
            String password = passwordField.getText();

            int port;
            try {
                port = Integer.parseInt(portStr);
            } catch (NumberFormatException e) {
                statusText.setFill(Color.web("#f38ba8"));
                statusText.setText("Nieprawidłowy port.");
                return;
            }

            if (login.isEmpty() || password.isEmpty()) {
                statusText.setFill(Color.web("#f38ba8"));
                statusText.setText("Podaj login i hasło.");
                return;
            }

            connectBtn.setDisable(true);
            statusText.setFill(Color.web("#fab387"));
            statusText.setText("Łączenie...");

            new Thread(() -> {
                try {
                    Socket socket = new Socket(host, port);
                    PrintWriter pw = new PrintWriter(new OutputStreamWriter(socket.getOutputStream(), StandardCharsets.UTF_8), true);
                    BufferedReader br = new BufferedReader(new InputStreamReader(socket.getInputStream(), StandardCharsets.UTF_8));

                    // KROK 1: Autoryzacja
                    JSONObject authReq = new JSONObject();
                    authReq.put("username", login);
                    authReq.put("password", password);
                    pw.println(authReq.toString());

                    String line = br.readLine();
                    if (line == null) throw new Exception("Brak odpowiedzi.");
                    JSONObject resp = new JSONObject(line);

                    if (!resp.optBoolean("ok", false)) {
                        Platform.runLater(() -> {
                            statusText.setFill(Color.web("#f38ba8"));
                            statusText.setText("✗ " + resp.optString("error", "Błąd logowania"));
                            connectBtn.setDisable(false);
                        });
                        socket.close();
                        return;
                    }

                    // KROK 2: Pobranie listy i zmiana widoku
                    String displayName = resp.optString("display_name", login);
                    JSONObject configs = resp.optJSONObject("available_configs");

                    Platform.runLater(() -> showConfigSelection(socket, displayName, configs, pw));

                } catch (Exception ex) {
                    Platform.runLater(() -> {
                        statusText.setFill(Color.web("#f38ba8"));
                        statusText.setText("Błąd: " + ex.getMessage());
                        connectBtn.setDisable(false);
                    });
                }
            }).start();
        };

        connectBtn.setOnAction(e -> doConnect.run());
        loginField.setOnAction(e -> doConnect.run());
        passwordField.setOnAction(e -> doConnect.run());

        Scene scene = new Scene(grid, 420, 360);
        primaryStage.setScene(scene);
        primaryStage.show();
    }

    /**
     * Dynamiczna lista konfiguracji z serwera.
     */
    private void showConfigSelection(Socket socket, String username, JSONObject configs, PrintWriter pw) {
        VBox layout = new VBox(10);
        layout.setAlignment(Pos.CENTER);
        layout.setPadding(new Insets(20));
        layout.setStyle("-fx-background-color: #1e1e2e;");

        Text info = new Text("Witaj, " + username + "!\nWybierz środowisko:");
        info.setFill(Color.web("#cdd6f4"));
        info.setFont(Font.font("Consolas", 14));
        layout.getChildren().add(info);

        if (configs != null) {
            for (String key : configs.keySet()) {
                Button b = new Button(configs.getString(key));
                b.setMaxWidth(Double.MAX_VALUE);
                b.setStyle("-fx-background-color: #45475a; -fx-text-fill: #cdd6f4; -fx-cursor: hand;");
                b.setOnAction(e -> {
                    try {
                        JSONObject choice = new JSONObject();
                        choice.put("config", key);
                        pw.println(choice.toString());

                        SocketTtyConnector connector = new SocketTtyConnector(socket);
                        terminalApp.showTerminal(new Stage(), username, connector);
                        primaryStage.close();
                    } catch (Exception ex) { ex.printStackTrace(); }
                });
                layout.getChildren().add(b);
            }
        }

        primaryStage.setScene(new Scene(layout, 350, 400));
    }
}