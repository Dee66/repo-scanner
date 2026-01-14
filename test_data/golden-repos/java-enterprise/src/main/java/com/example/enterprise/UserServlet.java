package com.example.enterprise;

import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.Statement;
import java.io.File;

public class UserServlet extends HttpServlet {

    protected void doGet(HttpServletRequest request, HttpServletResponse response)
            throws IOException {

        String userId = request.getParameter("id");

        try {
            // SQL Injection vulnerability
            Connection conn = DriverManager.getConnection("jdbc:mysql://localhost/db", "user", "password");
            Statement stmt = conn.createStatement();
            String query = "SELECT * FROM users WHERE id = " + userId;
            ResultSet rs = stmt.executeQuery(query);

            response.getWriter().write("User data retrieved");

        } catch (Exception e) {
            response.getWriter().write("Error: " + e.getMessage());
        }
    }

    protected void doPost(HttpServletRequest request, HttpServletResponse response)
            throws IOException {

        String filename = request.getParameter("filename");
        String content = request.getParameter("content");

        try {
            // Path traversal vulnerability
            File file = new File("/tmp/uploads/" + filename);
            java.io.FileWriter writer = new java.io.FileWriter(file);
            writer.write(content);
            writer.close();

            response.getWriter().write("File uploaded");

        } catch (Exception e) {
            response.getWriter().write("Error: " + e.getMessage());
        }
    }
}