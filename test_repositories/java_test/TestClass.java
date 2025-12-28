package com.example;

import java.util.List;
import java.util.ArrayList;

/**
 * A simple test class for Java adapter testing.
 */
public class TestClass {

    private String name;
    private int value;

    /**
     * Constructor for TestClass.
     * @param name the name
     * @param value the value
     */
    public TestClass(String name, int value) {
        this.name = name;
        this.value = value;
    }

    /**
     * Gets the name.
     * @return the name
     */
    public String getName() {
        return name;
    }

    /**
     * Sets the name.
     * @param name the name to set
     */
    public void setName(String name) {
        this.name = name;
    }

    /**
     * Gets the value.
     * @return the value
     */
    public int getValue() {
        return value;
    }

    /**
     * Processes the value.
     * @param multiplier the multiplier
     * @return the processed value
     */
    public int processValue(int multiplier) {
        if (multiplier > 0) {
            return value * multiplier;
        } else {
            return value;
        }
    }

    /**
     * Main method.
     * @param args command line arguments
     */
    public static void main(String[] args) {
        TestClass obj = new TestClass("test", 42);
        System.out.println(obj.getName());
    }
}