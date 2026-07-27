package com.example.terminalapp;

import javafx.application.Application;

public class Launcher {
    public static void main(String[] args) {
        if (System.getProperty("javafx.cachedir") == null) {
            System.setProperty("javafx.cachedir", System.getProperty("user.home") + "/.openjfx/cache_v20");
        }
        Application.launch(TerminalApp.class, args);
    }
}
