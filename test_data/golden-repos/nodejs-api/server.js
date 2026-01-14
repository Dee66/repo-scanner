const express = require('express');
const { exec } = require('child_process');
const fs = require('fs');
const app = express();

app.use(express.json());

app.get('/api/user/:id', (req, res) => {
  const userId = req.params.id;
  // SQL Injection vulnerability
  const query = `SELECT * FROM users WHERE id = ${userId}`;
  // Execute query (simulated)
  res.json({ user: `User ${userId}` });
});

app.get('/api/exec', (req, res) => {
  const cmd = req.query.cmd;
  // Command injection vulnerability
  exec(cmd, (error, stdout, stderr) => {
    res.json({ output: stdout });
  });
});

app.post('/api/upload', (req, res) => {
  const filename = req.body.filename;
  // Path traversal vulnerability
  const filepath = `/tmp/uploads/${filename}`;
  fs.writeFileSync(filepath, req.body.content);
  res.json({ status: 'uploaded' });
});

app.get('/api/config', (req, res) => {
  // Information disclosure
  res.json({
    databaseUrl: 'mongodb://user:password@localhost/db',
    apiKey: 'sk-nodejs-abcdef123456',
    secret: process.env.SECRET || 'default-secret'
  });
});

// No authentication required
app.delete('/api/user/:id', (req, res) => {
  const userId = req.params.id;
  // Direct deletion without auth
  res.json({ status: 'deleted', userId });
});

app.listen(3000, '0.0.0.0', () => {
  console.log('Server running on port 3000');
});