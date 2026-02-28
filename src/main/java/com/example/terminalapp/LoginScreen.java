package com.example.terminalapp;

import javafx.collections.FXCollections;
import javafx.collections.ObservableList;
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

public class LoginScreen {

    private Stage primaryStage;
    private TerminalApp terminalApp;
    private String username;
    private String selected_config;

    public LoginScreen(Stage primaryStage, TerminalApp terminalApp) {
        this.primaryStage = primaryStage;
        this.terminalApp = terminalApp;
    }

    public void show() {
        primaryStage.setTitle("Login");

        GridPane grid = new GridPane();
        grid.setAlignment(Pos.CENTER);
        grid.setHgap(10);
        grid.setVgap(10);
        grid.setPadding(new Insets(25, 25, 25, 25));

        Text scenetitle = new Text("Witaj!");
        scenetitle.setFont(Font.font("Consolas", FontWeight.NORMAL, 20));
        grid.add(scenetitle, 0, 0, 2, 1);

        Label userName = new Label("Nazwa użytkownika:");
        grid.add(userName, 0, 1);

        TextField userTextField = new TextField();
        grid.add(userTextField, 1, 1);

        Label pw = new Label("Hasło:");
        grid.add(pw, 0, 2);

        PasswordField pwBox = new PasswordField();
        grid.add(pwBox, 1, 2);

        ObservableList<String> configs = FXCollections.observableArrayList(
                "LinuxTerminal",
                "PowerShell",
                "WindowsTerminal",
                "bazy1"
        );
        ChoiceBox<String> confBox = new ChoiceBox<>(configs);
        confBox.getSelectionModel().selectFirst();
        grid.add(confBox, 0, 3);

        Button btn = new Button("Zaloguj");
        HBox hbBtn = new HBox(10);
        hbBtn.setAlignment(Pos.BOTTOM_RIGHT);
        hbBtn.getChildren().add(btn);
        grid.add(hbBtn, 1, 4);

        final Text actiontarget = new Text();
        grid.add(actiontarget, 1, 6);

        btn.setOnAction(e -> {
            if (authenticate(userTextField.getText(), pwBox.getText())) {
                username = userTextField.getText();
                selected_config = confBox.getValue();
                terminalApp.showTerminal(new Stage(), username,selected_config);
                primaryStage.close();
            } else {
                actiontarget.setFill(Color.FIREBRICK);
                actiontarget.setText("Authentication failed");
            }
        });
        Scene scene = new Scene(grid);
        primaryStage.setScene(scene);
        primaryStage.show();
    }

    private boolean authenticate(String username, String password) {
        return "admin".equals(username) && "password".equals(password);
    }
}
