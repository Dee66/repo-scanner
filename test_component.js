// Test JavaScript file for multi-language support
import React from 'react';

function App() {
  const [count, setCount] = React.useState(0);

  return (
    <div className="App">
      <h1>Hello World</h1>
      <button onClick={() => setCount(count + 1)}>
        Count: {count}
      </button>
    </div>
  );
}

export default App;