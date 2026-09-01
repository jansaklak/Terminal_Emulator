package com.example.terminalapp;

import javafx.application.Application;
import java.io.File;

public class Launcher {
    public static void main(String[] args) {
        if (System.getProperty("javafx.cachedir") == null) {
            String osName = System.getProperty("os.name", "generic").toLowerCase().replaceAll("[^a-z0-9]", "");
            String osArch = System.getProperty("os.arch", "generic").toLowerCase().replaceAll("[^a-z0-9]", "");
            String cachePath = System.getProperty("user.home") + File.separator + ".openjfx" + File.separator + "cache_v20_" + osName + "_" + osArch;
            System.setProperty("javafx.cachedir", cachePath);
        }
        Application.launch(TerminalApp.class, args);
    }
}

