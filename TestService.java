package com.example;

import java.util.List;
import java.util.ArrayList;

public class TestService {

    private List<String> items;

    public TestService() {
        this.items = new ArrayList<>();
    }

    public void addItem(String item) {
        this.items.add(item);
    }

    public List<String> getItems() {
        return this.items;
    }

    public static void main(String[] args) {
        TestService service = new TestService();
        service.addItem("test");
        System.out.println(service.getItems());
    }
}