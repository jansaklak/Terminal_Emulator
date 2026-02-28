package com.example.terminalapp;

import javafx.application.Application;
import javafx.application.Platform;
import javafx.geometry.Insets;
import javafx.geometry.Pos;
import javafx.scene.Scene;
import javafx.scene.control.*;
import javafx.scene.input.KeyCode;
import javafx.scene.input.KeyCodeCombination;
import javafx.scene.input.KeyCombination;
import javafx.scene.input.KeyEvent;
import javafx.scene.layout.HBox;
import javafx.scene.layout.Priority;
import javafx.scene.layout.VBox;
import javafx.stage.Stage;

import java.io.*;
import java.net.Socket;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;

public class TerminalApp extends Application {

    private static final String HISTORY_FILE = "command_history.txt";
    private TextArea outputArea;
    private TextField inputField;
    private VBox root;

    private String username;
    private String selected_config;

    // Komunikacja sieciowa
    private Socket socket;
    private PrintWriter out;
    private BufferedReader in;

    // Przywrócone Twoje style
    private static final String DARK_OUTPUT = "-fx-control-inner-background: black; -fx-text-fill: lime; -fx-font-family: 'Consolas', 'Monospaced'";
    private static final String DARK_INPUT = "-fx-background-color: #333; -fx-text-fill: white; -fx-font-family: 'Consolas', 'Monospaced'";
    private static final String DARK_ROOT = "-fx-background-color: #222;";

    private static final String LIGHT_OUTPUT = "-fx-control-inner-background: white; -fx-text-fill: black; -fx-font-family: 'Consolas', 'Monospaced'";
    private static final String LIGHT_INPUT = "-fx-background-color: #f4f4f4; -fx-text-fill: black; -fx-font-family: 'Consolas', 'Monospaced'; -fx-border-color: #ccc";
    private static final String LIGHT_ROOT = "-fx-background-color: #ddd;";

    private int font_size = 14;
    private List<String> command_history = new ArrayList<>();
    private int curr_command_index = 0;

    KeyCombination ctrlC = new KeyCodeCombination(KeyCode.C, KeyCombination.CONTROL_DOWN);

    @Override
    public void start(Stage primaryStage) {
        LoginScreen loginScreen = new LoginScreen(primaryStage, this);
        loginScreen.show();
    }

    public void showTerminal(Stage primaryStage, String username_, String _selected_config) {
        username = username_;
        selected_config = _selected_config;

        outputArea = new TextArea();
        outputArea.setEditable(false);
        outputArea.setWrapText(true);
        inputField = new TextField();
        inputField.setPromptText("Wpisz polecenie...");

        Label themeLabel = new Label("Motyw:");
        themeLabel.setStyle("-fx-text-fill: grey;");

        ComboBox<String> themeSelector = new ComboBox<>();
        themeSelector.getItems().addAll("Ciemny", "Jasny");
        themeSelector.setValue("Ciemny");
        themeSelector.setPrefWidth(100);


        // Przycisk Reset
        Button resetButton = new Button("Restart Sesji");
        resetButton.setOnAction(event -> {
            restartServerSession();
            outputArea.clear();
            appendToTerminal("[SYSTEM] Sesja i baza danych zostały zrestartowane.");
        });

        Button zoomInButton = new Button("Powieksz (+)");
        zoomInButton.setOnAction(actionEvent -> {
            if (font_size < 40) {
                font_size += 2;
                applyTheme(themeSelector.getValue());
            }
        });

        Button zoomOutButton = new Button("Pomniejsz (-)");
        zoomOutButton.setOnAction(actionEvent -> {
            if (font_size > 8) {
                font_size -= 2;
                applyTheme(themeSelector.getValue());
            }
        });

        HBox topPanel = new HBox(10);
        topPanel.setAlignment(Pos.CENTER_LEFT);
        topPanel.setPadding(new Insets(5));
        topPanel.setStyle("-fx-background-color: #ccc;");
        topPanel.getChildren().addAll(themeLabel, themeSelector, resetButton, zoomInButton, zoomOutButton);

        root = new VBox(5, topPanel, outputArea, inputField);
        root.setPadding(new Insets(0, 10, 10, 10));
        VBox.setVgrow(outputArea, Priority.ALWAYS);

        applyTheme("Ciemny");
        connectToServer(); // Nawiązanie połączenia

        themeSelector.setOnAction(event -> applyTheme(themeSelector.getValue()));

        // Obsługa TAB - autouzupełniania
        inputField.addEventFilter(KeyEvent.KEY_PRESSED, event -> {
            if (event.getCode() == KeyCode.TAB) {
                String currentText = inputField.getText().trim();
                if (!currentText.isEmpty() && out != null) {
                    out.println("TAB_REQ:" + currentText);
                }
                event.consume();
            }
        });
        inputField.setOnKeyPressed(event -> {
            if (event.getCode() == KeyCode.ENTER) {
                String command = inputField.getText();
                if (!command.trim().isEmpty()) {
                    executeCommand(command);
                    logCommandToFile(command);
                    inputField.clear();
                    curr_command_index = command_history.size();
                }
            }   else if (ctrlC.match(event)){
//                Obsługa Ctrl+C - do poprawy
            if (out != null) {
                out.println("__SIGINT__");
            }
            inputField.clear();
            event.consume();
        }
        });

        Scene scene = new Scene(root, 1024, 768);
        primaryStage.setTitle("Terminal: " + username + "#" + selected_config);
        primaryStage.setScene(scene);
        primaryStage.show();

        appendToTerminal("Połączono z konfiguracją: " + selected_config);
    }

    // NIE dodaje \n na końcu
    private void appendRawText(String text) {
        Platform.runLater(() -> outputArea.appendText(text));
    }

    // ConnectToServer czyta surowe bajty
    private void connectToServer() {
        new Thread(() -> {
            try {
                socket = new Socket("127.0.0.1", 5000);
                out = new PrintWriter(socket.getOutputStream(), true);

                InputStream inStream = socket.getInputStream();

                byte[] buffer = new byte[4096];
                int length;

                while ((length = inStream.read(buffer)) != -1) {
                    String received = new String(buffer, 0, length);
                    appendRawText(received);   // Wyświetlanie surowego TTY
                }

            } catch (IOException e) {
                Platform.runLater(() ->
                        outputArea.appendText("\n[ERROR] Rozłączono z serwerem.\n")
                );
            }
        }).start();
    }
    
    private void executeCommand(String command) {
        if (out != null) {
            out.println(command); // Wysyłanie do serwera
            command_history.add(command);
        }
    }

    // Restart tworzy nową sesję
    private void restartServerSession() {
        try {
            if (socket != null) {
                socket.close();
            }
        } catch (IOException ignored) {}

        outputArea.clear();
        appendToTerminal("[SYSTEM] Restartowanie sesji...");

        connectToServer();
    }

    //Jasny/ciemny motyw
    private void applyTheme(String themeName) {
        String sizeStyle = "; -fx-font-size: " + font_size + "px;";
        if ("Jasny".equals(themeName)) {
            outputArea.setStyle(LIGHT_OUTPUT + sizeStyle);
            inputField.setStyle(LIGHT_INPUT + sizeStyle);
            root.setStyle(LIGHT_ROOT);
        } else {
            outputArea.setStyle(DARK_OUTPUT + sizeStyle);
            inputField.setStyle(DARK_INPUT + sizeStyle);
            root.setStyle(DARK_ROOT);
        }
    }

    // Strzałka w góre - póki co nie działa
    private void updateInputFromHistory() {
        if (curr_command_index >= 0 && curr_command_index < command_history.size()) {
            String historyCmd = command_history.get(curr_command_index);
            inputField.setText(historyCmd);
            inputField.positionCaret(historyCmd.length());
        }
    }

    // Log do pliku
    private void logCommandToFile(String command) {
        String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
        String logEntry = String.format("[%s] %s%n", timestamp, command);
        try {
            Files.write(Paths.get(HISTORY_FILE), logEntry.getBytes(), StandardOpenOption.CREATE, StandardOpenOption.APPEND);
        } catch (IOException e) {

        }
    }

    private void appendToTerminal(String text) {
        outputArea.appendText(text + "\n");
    }
}