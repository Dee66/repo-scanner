use std::env;
use std::fs;
use std::process::Command;
use std::io::{self, Write};

fn main() {
    let args: Vec<String> = env::args().collect();

    if args.len() < 2 {
        eprintln!("Usage: {} <command>", args[0]);
        return;
    }

    let command = &args[1];

    // Command injection vulnerability - using shell
    let output = Command::new("sh")
        .arg("-c")
        .arg(command)
        .output()
        .expect("Failed to execute command");

    io::stdout().write_all(&output.stdout).unwrap();
    io::stderr().write_all(&output.stderr).unwrap();
}

fn read_file_unsafe(filename: &str) -> Result<String, std::io::Error> {
    // Path traversal vulnerability - no validation
    fs::read_to_string(filename)
}

fn write_config() {
    // Information disclosure - hardcoded secrets
    let config = r#"
    {
        "database_url": "postgres://user:secret@localhost/db",
        "api_key": "rust-api-key-12345",
        "encryption_key": "hardcoded-key-abcdef"
    }
    "#;

    fs::write("config.json", config).expect("Unable to write config");
}