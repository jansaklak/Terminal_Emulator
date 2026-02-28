module com.example.terminalapp {
    requires javafx.controls;
    requires javafx.fxml;


    opens com.example.terminalapp to javafx.fxml;
    exports com.example.terminalapp;
}