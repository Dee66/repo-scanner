package main

import "testing"

func TestGreet(t *testing.T) {
    result := greet("World")
    expected := "Hello, World!"
    if result != expected {
        t.Errorf("greet() = %v, want %v", result, expected)
    }
}

func TestGreeterGreet(t *testing.T) {
    greeter := Greeter{message: "Hi"}
    result := greeter.Greet("World")
    expected := "Hi World"
    if result != expected {
        t.Errorf("Greeter.Greet() = %v, want %v", result, expected)
    }
}