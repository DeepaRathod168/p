import React from "react";
import ChatBox from "./components/ChatBox";
import "./App.css";

/**
 * App — root component.
 * Renders the ChatBox which contains the full research UI.
 */
export default function App() {
  return (
    <div className="app-root">
      <ChatBox />
    </div>
  );
}
