package com.example.terminalapp;

import com.jediterm.terminal.ui.JediTermWidget;
import com.jediterm.terminal.ui.settings.DefaultSettingsProvider;
import javafx.application.Application;
import javafx.application.Platform;
import javafx.embed.swing.SwingNode;
import javafx.scene.Scene;
import javafx.scene.control.Button;
import javafx.scene.control.Tooltip;
import javafx.scene.layout.BorderPane;
import javafx.scene.layout.HBox;
import javafx.stage.Stage;

import javax.swing.*;
import java.awt.*;

/**
 * Główna aplikacja JavaFX.
 *
 * Uruchamia się od ekranu logowania (LoginScreen); po poprawnej autoryzacji
 * wywoływana jest metoda showTerminal() z otwartym połączeniem SocketTtyConnector.
 *
 * Okno terminala zawiera pasek narzędzi z przyciskiem "Restart sesji".
 */
public class TerminalApp extends Application {

    @Override
    public void start(Stage primaryStage) {
        com.example.terminalapp.LoginScreen loginScreen = new com.example.terminalapp.LoginScreen(primaryStage, this);
        loginScreen.show();
    }

    /**
     * Otwiera okno terminala dla już uwierzytelnionego połączenia.
     *
     * @param stage     Nowy, pusty Stage dla terminala.
     * @param username  Nazwa użytkownika wyświetlana w tytule okna.
     * @param connector Uwierzytelniony obiekt {@link com.example.terminalapp.SocketTtyConnector}.
     */
    public void showTerminal(Stage stage, String username, com.example.terminalapp.SocketTtyConnector connector) {
        BorderPane root = new BorderPane();
        root.setStyle("-fx-background-color: #1e1e2e;");

        // Pasek narzędzi
        Button restartBtn = new Button("⟳  Restart sesji");
        restartBtn.setStyle(
                "-fx-background-color: #45475a; -fx-text-fill: #cdd6f4; " +
                        "-fx-cursor: hand; -fx-border-radius: 4; -fx-background-radius: 4;");
        restartBtn.setTooltip(new Tooltip(
                "Zamyka bieżące połączenie i otwiera nowe okno logowania.\n" +
                        "Historia poleceń zostanie utracona."));

        HBox toolbar = new HBox(restartBtn);
        toolbar.setStyle("-fx-background-color: #181825; -fx-padding: 4 8;");
        root.setTop(toolbar);

        // Terminal
        SwingNode swingNode = new SwingNode();
        root.setCenter(swingNode);

        SwingUtilities.invokeLater(() -> {
            JediTermWidget widget = new JediTermWidget(new DefaultSettingsProvider());
            widget.setTtyConnector(connector);
            widget.setPreferredSize(new Dimension(1000, 680));
            swingNode.setContent(widget);
            widget.start();
        });

        // Akcja restartu
        restartBtn.setOnAction(e -> {
            connector.close();      // Rozłączenie z serwerem
            stage.close();          // Zamknięcie okna terminala

            // Otwarcie świeżego ekranu logowania
            Platform.runLater(() -> {
                Stage loginStage = new Stage();
                com.example.terminalapp.LoginScreen loginScreen = new com.example.terminalapp.LoginScreen(loginStage, this);
                loginScreen.show();
            });
        });

        // Zamknięcie połączenia przy zamknięciu okna przyciskiem X
        stage.setOnCloseRequest(e -> connector.close());

        stage.setScene(new Scene(root, 1000, 720));
        stage.setTitle("Terminal – " + username);
        stage.show();
    }

    /**
     * Wywoływane, gdy aplikacja JavaFX powinna się zakończyć.
     * Wymuszamy zamknięcie całego procesu JVM, aby ubić wątki Swing i biblioteki terminala.
     */
    @Override
    public void stop() {
        Platform.exit();
        System.exit(0);
    }

    public static void main(String[] args) {
        launch(args);
    }
}
