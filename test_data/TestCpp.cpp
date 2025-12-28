// Test C++ file for adapter validation

#include <iostream>
#include <string>
#include <vector>

// A simple function
std::string greet(const std::string& name) {
    return "Hello, " + name + "!";
}

// A class with methods
class Greeter {
private:
    std::string message_;

public:
    Greeter(const std::string& message) : message_(message) {}

    std::string greet(const std::string& name) const {
        return message_ + " " + name;
    }
};

// A struct
struct User {
    std::string name;
    std::string email;
};

// A template function
template<typename T>
T add(T a, T b) {
    return a + b;
}

// A constant
const int MAX_RETRIES = 3;

// A global variable
int defaultPort = 8080;

int main() {
    Greeter greeter("Hi");
    std::cout << greeter.greet("World") << std::endl;
    return 0;
}