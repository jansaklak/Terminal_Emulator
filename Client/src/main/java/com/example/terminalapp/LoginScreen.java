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
import javafx.stage.FileChooser;
import javafx.stage.Stage;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.File;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Okno logowania
 */
public class LoginScreen {

    private static final String DEFAULT_HOST = "127.0.0.1";
    private static final int    DEFAULT_PORT = 51234;

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
        TextField loginField = new TextField("adam_kow");
        loginField.setPromptText("użytkownik");
        loginField.setStyle("-fx-background-color: #313244; -fx-text-fill: #cdd6f4; -fx-prompt-text-fill: #585b70;");
        grid.add(loginField, 1, 3);

        // Hasło
        Label passwordLabel = new Label("Hasło:");
        passwordLabel.setTextFill(Color.web("#a6adc8"));
        grid.add(passwordLabel, 0, 4);
        PasswordField passwordField = new PasswordField();
        passwordField.setText("ea332f1f");
        passwordField.setPromptText("hasło");
        passwordField.setStyle("-fx-background-color: #313244; -fx-text-fill: #cdd6f4; -fx-prompt-text-fill: #585b70;");
        grid.add(passwordField, 1, 4);

        // Motyw
        Label themeLabel = new Label("Motyw:");
        themeLabel.setTextFill(Color.web("#a6adc8"));
        grid.add(themeLabel, 0, 5);
        
        ToggleGroup themeGroup = new ToggleGroup();
        RadioButton darkRadio = new RadioButton("Ciemny");
        darkRadio.setTextFill(Color.web("#cdd6f4"));
        darkRadio.setToggleGroup(themeGroup);
        darkRadio.setSelected(true);
        
        RadioButton lightRadio = new RadioButton("Jasny");
        lightRadio.setTextFill(Color.web("#cdd6f4"));
        lightRadio.setToggleGroup(themeGroup);
        
        HBox themeBox = new HBox(10, darkRadio, lightRadio);
        grid.add(themeBox, 1, 5);

        // Przycisk
        Button connectBtn = new Button("Zaloguj");
        connectBtn.setStyle("-fx-background-color: #89b4fa; -fx-text-fill: #1e1e2e; -fx-font-weight: bold; -fx-cursor: hand;");
        HBox btnBox = new HBox(connectBtn);
        btnBox.setAlignment(Pos.BOTTOM_RIGHT);
        grid.add(btnBox, 1, 6);

        Text statusText = new Text();
        statusText.setFont(Font.font("Consolas", 12));
        grid.add(statusText, 0, 7, 2, 1);

        Runnable doConnect = () -> {
            String host = hostField.getText().trim();
            String portStr = portField.getText().trim();
            String login = loginField.getText().trim();
            String password = passwordField.getText();
            boolean isDark = darkRadio.isSelected();

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
                    Map<String, Boolean> recordingPermissions = new HashMap<>();
                    Map<String, Boolean> autoExecutePermissions = new HashMap<>();

                    if (configs != null) {
                        for (String key : configs.keySet()) {
                            Object raw = configs.get(key);
                            if (raw instanceof JSONObject cfgObj) {
                                recordingPermissions.put(key, cfgObj.optBoolean("can_record_commands", false));
                                autoExecutePermissions.put(key, cfgObj.optBoolean("can_auto_execute", false));
                            }
                        }
                    }

                    Platform.runLater(() -> showConfigSelection(socket, br, displayName, configs, recordingPermissions, autoExecutePermissions, pw, isDark));

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

    private void launchEnvironment(Socket socket, BufferedReader br, String username, String configKey, Map<String, Boolean> recordingPermissions, Map<String, Boolean> autoExecutePermissions, PrintWriter pw, boolean isDark, byte[] autoLoadCmdsData, boolean resetContainer) {
        try {
            JSONObject choice = new JSONObject();
            choice.put("config", configKey);
            if (resetContainer) {
                choice.put("reset", true);
            }
            pw.println(choice.toString());

            boolean canRecordCommands = recordingPermissions.getOrDefault(configKey, false);
            boolean canAutoExecute = autoExecutePermissions.getOrDefault(configKey, false);

            String line = null;
            try {
                line = br.readLine();
            } catch (Exception ignored) { }

            if (line != null) {
                try {
                    JSONObject sessionResp = new JSONObject(line);
                    JSONObject perms = sessionResp.optJSONObject("permissions");
                    if (perms != null) {
                        canRecordCommands = perms.optBoolean("can_record_commands", canRecordCommands);
                        canAutoExecute = perms.optBoolean("can_auto_execute", canAutoExecute);
                    }
                } catch (Exception ignored) { }
            }

            SocketTtyConnector connector = new SocketTtyConnector(socket);

            if (autoLoadCmdsData != null && autoLoadCmdsData.length > 0) {
                // Bezpieczne wczytanie poleceń po ustabilizowaniu sesji
                new Thread(() -> {
                    try {
                        Thread.sleep(800);
                        connector.requestLoadCommands(autoLoadCmdsData);
                    } catch (Exception ex) {
                        ex.printStackTrace();
                    }
                }).start();
            }

            terminalApp.showTerminal(new Stage(), username, connector, isDark, canRecordCommands, canAutoExecute);
            primaryStage.close();
        } catch (Exception ex) {
            ex.printStackTrace();
        }
    }

    private void showConfigSelection(Socket socket, BufferedReader br, String username, JSONObject configs, Map<String, Boolean> recordingPermissions, Map<String, Boolean> autoExecutePermissions, PrintWriter pw, boolean isDark) {
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
                String label = key;
                Object raw = configs.get(key);
                if (raw instanceof JSONObject cfgObj) {
                    label = cfgObj.optString("description", key);
                } else if (raw instanceof String s) {
                    label = s;
                }

                Button b = new Button(label);
                b.setMaxWidth(Double.MAX_VALUE);
                b.setStyle("-fx-background-color: #45475a; -fx-text-fill: #cdd6f4; -fx-cursor: hand;");
                b.setOnAction(e -> launchEnvironment(socket, br, username, key, recordingPermissions, autoExecutePermissions, pw, isDark, null, false));
                layout.getChildren().add(b);
            }
        }

        Separator sep = new Separator();
        sep.setPadding(new Insets(5, 0, 5, 0));
        layout.getChildren().add(sep);

        Button loadCmdsBtn = new Button("📁 Wczytaj plik .cmds");
        loadCmdsBtn.setMaxWidth(Double.MAX_VALUE);
        loadCmdsBtn.setStyle("-fx-background-color: #89b4fa; -fx-text-fill: #1e1e2e; -fx-font-weight: bold; -fx-cursor: hand;");

        loadCmdsBtn.setOnAction(e -> {
            try {
                FileChooser fc = new FileChooser();
                fc.setTitle("Wybierz plik komend (.cmds)");
                fc.getExtensionFilters().add(new FileChooser.ExtensionFilter("Pliki komend (*.cmds)", "*.cmds", "*.txt"));
                File selectedFile = fc.showOpenDialog(primaryStage);
                if (selectedFile == null) return;

                byte[] fileData = java.nio.file.Files.readAllBytes(selectedFile.toPath());
                String filenameLower = selectedFile.getName().toLowerCase();
                String fileContentStr = new String(fileData, StandardCharsets.UTF_8).toLowerCase();

                String matchedKey = null;
                if (configs != null && !configs.isEmpty()) {
                    List<String> keys = new ArrayList<>(configs.keySet());
                    keys.sort((k1, k2) -> Integer.compare(k2.length(), k1.length()));

                    for (String key : keys) {
                        String keyLower = key.toLowerCase();
                        if (filenameLower.contains(keyLower) || fileContentStr.contains(keyLower)) {
                            matchedKey = key;
                            break;
                        }
                    }
                }

                if (matchedKey != null) {
                    launchEnvironment(socket, br, username, matchedKey, recordingPermissions, autoExecutePermissions, pw, isDark, fileData, true);
                } else {
                    Alert alert = new Alert(Alert.AlertType.WARNING);
                    alert.setTitle("Rozpoznawanie obrazu");
                    alert.setHeaderText("Nie rozpoznano automatycznie obrazu z pliku .cmds.");
                    alert.setContentText("Nazwa pliku nie zawiera nazwy znanego środowiska.");
                    alert.showAndWait();
                }
            } catch (Exception ex) {
                ex.printStackTrace();
            }
        });

        layout.getChildren().add(loadCmdsBtn);

        primaryStage.setScene(new Scene(layout, 380, 440));
    }
}