package com.example.terminalapp;

import com.jediterm.terminal.ui.JediTermWidget;
import com.jediterm.terminal.ui.settings.DefaultSettingsProvider;
import com.jediterm.terminal.ui.settings.SettingsProvider;
import javafx.application.Application;
import javafx.application.Platform;
import javafx.embed.swing.SwingNode;
import javafx.scene.Scene;
import javafx.scene.control.Button;
import javafx.scene.control.Alert;
import javafx.stage.FileChooser;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import javafx.scene.layout.BorderPane;
import javafx.scene.layout.HBox;
import javafx.stage.Stage;

import javax.swing.*;
import java.awt.*;
import java.awt.event.KeyAdapter;
import java.awt.event.KeyEvent;
import java.awt.event.MouseAdapter;
import java.awt.event.MouseEvent;
import java.lang.reflect.Field;
import java.lang.reflect.Method;

public class TerminalApp extends Application {

    private static class MySettings extends DefaultSettingsProvider {
        float fontSize = 16f;
        boolean isDark;

        MySettings(boolean isDark) {
            this.isDark = isDark;
        }

        @Override
        public float getTerminalFontSize() {
            return fontSize;
        }

        @Override
        public com.jediterm.terminal.emulator.ColorPalette getTerminalColorPalette() {
            return new com.jediterm.terminal.emulator.ColorPalette() {
                @Override
                public com.jediterm.core.Color getForegroundByColorIndex(int i) {
                    return isDark ? new com.jediterm.core.Color(205, 214, 244) : new com.jediterm.core.Color(0, 0, 0);
                }
                @Override
                public com.jediterm.core.Color getBackgroundByColorIndex(int i) {
                    return isDark ? new com.jediterm.core.Color(30, 30, 46) : new com.jediterm.core.Color(255, 255, 255);
                }
            };
        }
    }

    private static class MyJediTermWidget extends JediTermWidget {
        public MyJediTermWidget(SettingsProvider settingsProvider) {
            super(settingsProvider);
        }

        public void refreshTerminal() {
            try {
                Method method = myTerminalPanel.getClass().getDeclaredMethod("reinitFontAndResize");
                method.setAccessible(true);
                method.invoke(myTerminalPanel);
                myTerminalPanel.repaint();
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }

    @Override
    public void start(Stage primaryStage) {
        new LoginScreen(primaryStage, this).show();
    }

    public void showTerminal(Stage stage, String username, SocketTtyConnector connector, boolean isDark, boolean canRecordCommands, boolean canAutoExecute) {
        BorderPane root = new BorderPane();
        
        String bgColor = isDark ? "#1e1e2e" : "#ffffff";
        String toolbarColor = isDark ? "#181825" : "#f0f0f0";
        String btnStyle = isDark 
            ? "-fx-background-color: #45475a; -fx-text-fill: #cdd6f4; -fx-cursor: hand; -fx-border-radius: 4; -fx-background-radius: 4;"
            : "-fx-background-color: #e0e0e0; -fx-text-fill: #333333; -fx-cursor: hand; -fx-border-radius: 4; -fx-background-radius: 4;";

        root.setStyle("-fx-background-color: " + bgColor + ";");

        Button restartBtn = new Button("⟳ Reset");
        Button clearBtn = new Button("Clear");
        restartBtn.setStyle(btnStyle);
        clearBtn.setStyle(btnStyle);
        Button zoomInBtn = new Button("+");
        zoomInBtn.setStyle(btnStyle);
        Button zoomOutBtn = new Button("-");
        zoomOutBtn.setStyle(btnStyle);
        Button saveCmdBtn = new Button("Save cmds");
        saveCmdBtn.setStyle(btnStyle);

        saveCmdBtn.setDisable(!canRecordCommands);

        HBox toolbar = new HBox(10, clearBtn, restartBtn, zoomOutBtn, zoomInBtn, saveCmdBtn);
        toolbar.setStyle("-fx-background-color: " + toolbarColor + "; -fx-padding: 4 8;");
        root.setTop(toolbar);

        SwingNode swingNode = new SwingNode();
        root.setCenter(swingNode);

        MySettings settings = new MySettings(isDark);

        SwingUtilities.invokeLater(() -> {
            MyJediTermWidget widget = new MyJediTermWidget(settings);
            widget.getTerminalPanel().setBackground(isDark ? new Color(30, 30, 46) : Color.WHITE);
            widget.getTerminalPanel().setForeground(isDark ? new Color(205, 214, 244) : Color.BLACK);

            widget.getTerminalPanel().addMouseListener(new MouseAdapter() {
                @Override
                public void mousePressed(MouseEvent e) {
                    widget.getTerminalPanel().requestFocusInWindow();
                }
            });

            widget.setTtyConnector(connector);
            widget.setPreferredSize(new Dimension(1000, 680));
            swingNode.setContent(widget);
            
            /* 
            // --- LOGIKA PRZECHWYTYWANIA KOMEND Z EKRANU ---
            // Wyłączone na rzecz surowego logowania po stronie serwera (wierniejsze odtwarzanie)
            widget.getTerminalPanel().addKeyListener(new KeyAdapter() {
                @Override
                public void keyPressed(KeyEvent e) {
                    if (e.getKeyCode() == KeyEvent.VK_ENTER) {
                        String command = getFullCommandLine(widget);
                        if (command != null && !command.isEmpty() && canRecordCommands) {
                            try {
                                connector.requestAppendCommand(command);
                            } catch (Exception ex) { ex.printStackTrace(); }
                        }
                    }
                }
            });
            */

            widget.start();
            widget.requestFocusInWindow();

            Platform.runLater(() -> {
                zoomInBtn.setOnAction(e -> {
                    settings.fontSize += 2f;
                    SwingUtilities.invokeLater(widget::refreshTerminal);
                    swingNode.requestFocus();
                });
                zoomOutBtn.setOnAction(e -> {
                    if (settings.fontSize > 8f) {
                        settings.fontSize -= 2f;
                        SwingUtilities.invokeLater(widget::refreshTerminal);
                        swingNode.requestFocus();
                    }
                });
                saveCmdBtn.setOnAction(ev -> {
                    if (!canRecordCommands) return;
                    FileChooser fc = new FileChooser();
                    fc.setTitle("Zapisz komendy");
                    fc.getExtensionFilters().add(new FileChooser.ExtensionFilter("Pliki komend", "*.cmds", "*.txt"));
                    File target = fc.showSaveDialog(stage);
                    if (target == null) return;
                    if (!target.getName().contains(".")) {
                        target = new File(target.getParentFile(), target.getName() + ".cmds");
                    }
                    
                    final File finalTarget = target;
                    saveCmdBtn.setDisable(true);
                    saveCmdBtn.setText("Saving...");

                    new Thread(() -> {
                        try {
                            String commands = connector.getRecordedCommandsText();
                            try (FileOutputStream out = new FileOutputStream(finalTarget)) {
                                out.write(commands.getBytes(StandardCharsets.UTF_8));
                            }
                            Platform.runLater(() -> {
                                saveCmdBtn.setDisable(false);
                                saveCmdBtn.setText("Save cmds");
                                swingNode.requestFocus();
                            });
                        } catch (Exception ex) {
                            ex.printStackTrace();
                            Platform.runLater(() -> {
                                saveCmdBtn.setDisable(false);
                                saveCmdBtn.setText("Save cmds");
                                new Alert(Alert.AlertType.ERROR, "Błąd zapisu: " + ex.getMessage()).show();
                            });
                        }
                    }).start();
                });
            });
        });

        restartBtn.setOnAction(e -> {
            try { connector.requestReset(); } catch (Exception ex) { ex.printStackTrace(); }
            connector.close();
            stage.close();
            Platform.runLater(() -> {
                Stage loginStage = new Stage();
                new LoginScreen(loginStage, this).show();
            });
        });

        clearBtn.setOnAction(e -> {
            try { connector.requestClear(); } catch (Exception ex) { ex.printStackTrace(); }
            swingNode.requestFocus();
        });

        stage.setOnCloseRequest(e -> connector.close());
        stage.setScene(new Scene(root, 1000, 720));
        stage.setTitle("Terminal – " + username);
        stage.show();
        Platform.runLater(swingNode::requestFocus);
    }

    private String getFullCommandLine(JediTermWidget widget) {
        try {
            Object panel = widget.getTerminalPanel();
            Class<?> clazz = panel.getClass();
            Field terminalField = null;
            while (clazz != null) {
                try {
                    terminalField = clazz.getDeclaredField("myTerminal");
                    break;
                } catch (NoSuchFieldException e) {
                    clazz = clazz.getSuperclass();
                }
            }
            if (terminalField == null) return null;
            
            terminalField.setAccessible(true);
            Object terminal = terminalField.get(panel);

            Method getCursorYMethod = terminal.getClass().getMethod("getCursorY");
            int y = (int) getCursorYMethod.invoke(terminal);

            Method getLineTextMethod = terminal.getClass().getMethod("getLineText", int.class);
            String line = (String) getLineTextMethod.invoke(terminal, y - 1);

            if (line == null) return null;

            // Oczyszczanie z promptu
            String cmd = line.trim();
            int lastPromptIdx = -1;
            String[] prompts = {"$", "#", ">"};
            for (String p : prompts) {
                int idx = cmd.lastIndexOf(p);
                if (idx > lastPromptIdx) lastPromptIdx = idx;
            }
            if (lastPromptIdx != -1) {
                cmd = cmd.substring(lastPromptIdx + 1).trim();
            }
            return cmd;
        } catch (Exception ex) {
            return null;
        }
    }

    @Override
    public void stop() {
        Platform.exit();
        System.exit(0);
    }

    public static void main(String[] args) {
        launch(args);
    }
}
