#include <gtest/gtest.h>
#include "TestCpp.cpp"

// Test the greet function
TEST(GreetTest, BasicGreeting) {
    std::string result = greet("World");
    EXPECT_EQ(result, "Hello, World!");
}

// Test the Greeter class
TEST(GreeterTest, ClassGreeting) {
    Greeter greeter("Hi");
    std::string result = greeter.greet("World");
    EXPECT_EQ(result, "Hi World");
}

// Test the template function
TEST(TemplateTest, AddIntegers) {
    int result = add(2, 3);
    EXPECT_EQ(result, 5);
}

TEST(TemplateTest, AddStrings) {
    std::string result = add(std::string("Hello"), std::string(" World"));
    EXPECT_EQ(result, "Hello World");
}