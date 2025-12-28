// Test Go file for adapter validation

package main

import (
	"fmt"
	"net/http"
)

// A simple function
func greet(name string) string {
	return fmt.Sprintf("Hello, %s!", name)
}

// A method on a struct
type Greeter struct {
	message string
}

func (g Greeter) Greet(name string) string {
	return fmt.Sprintf("%s %s", g.message, name)
}

// A struct
type User struct {
	Name  string
	Email string
}

// An interface
type Writer interface {
	Write(data []byte) (int, error)
}

// A constant
const MaxRetries = 3

// A variable
var DefaultPort = 8080

func main() {
	greeter := Greeter{message: "Hi"}
	fmt.Println(greeter.Greet("World"))
}