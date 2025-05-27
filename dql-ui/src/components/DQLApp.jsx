import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

// Helper to format timestamps to MM/dd/yyyy H:M a
function formatTimestamp(ts) {
  if (!ts) return "";
  // Try to parse as MM/dd/yyyy H:M a, otherwise try ISO, otherwise return as is
  const date = new Date(ts);
  if (!isNaN(date.getTime())) {
    // Format to MM/dd/yyyy H:M a
    const pad = n => n.toString().padStart(2, '0');
    let hours = date.getHours();
    const ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12;
    hours = hours ? hours : 12; // the hour '0' should be '12'
    return `${pad(date.getMonth() + 1)}/${pad(date.getDate())}/${date.getFullYear()} ${pad(hours)}:${pad(date.getMinutes())} ${ampm}`;
  }
  return ts;
}

const DQLApp = () => {
  const [input, setInput] = useState("");
  const [generatedQuery, setGeneratedQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showHelp, setShowHelp] = useState(false);
  const [showDQLInfo, setShowDQLInfo] = useState(false);
  const [queryHistory, setQueryHistory] = useState([]);
  const [currentQueryData, setCurrentQueryData] = useState(null); // To store input, query, timestamp
  const [feedbackGiven, setFeedbackGiven] = useState(false); // Track feedback for the current query
  const [showCommentModal, setShowCommentModal] = useState(false);
  const [commentText, setCommentText] = useState("");
  const [pendingFeedbackType, setPendingFeedbackType] = useState(null); // 'good' or 'bad'

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    setIsLoading(true);
    try {
      const res = await fetch("http://localhost:8000/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: input })
      });
      const data = await res.json();
      const newQueryData = { input, query: data.dql, timestamp: data.timestamp };
      setGeneratedQuery(data.dql);
      setCurrentQueryData(newQueryData); // Store current query details
      setFeedbackGiven(false); // Reset feedback status for new query
      setQueryHistory([newQueryData, ...queryHistory]);
    } catch (error) {
      setGeneratedQuery("-- Error contacting backend");
      setCurrentQueryData(null); // Clear current query data on error
      setFeedbackGiven(false);
      console.error(error);
    }
    setIsLoading(false);
  };

  const handleFeedbackClick = (feedbackType) => {
    if (feedbackGiven || !currentQueryData) return;
    setPendingFeedbackType(feedbackType);
    setShowCommentModal(true);
  };

  const submitFeedback = async (comment) => {
    if (feedbackGiven || !currentQueryData || !pendingFeedbackType) return;
    setFeedbackGiven(true);
    setShowCommentModal(false);
    setCommentText("");
    try {
      await fetch("http://localhost:8000/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...currentQueryData,
          feedback: pendingFeedbackType, // 'good' or 'bad'
          comment: comment || ""
        })
      });
      setPendingFeedbackType(null);
      // Optionally: Show a confirmation message to the user
      console.log("Feedback submitted:", pendingFeedbackType, comment);
    } catch (error) {
      console.error("Error submitting feedback:", error);
      setFeedbackGiven(false);
      setPendingFeedbackType(null);
    }
  };

  const useExample = (text) => setInput(text);
  const copyToClipboard = () => navigator.clipboard.writeText(generatedQuery);

  return (
    <div className="flex flex-col h-screen bg-gray-100 px-8"> {/* Added px-8 here */}
      <header className="bg-blue-600 text-white p-4 -mx-8"> {/* Adjust header padding if needed due to parent padding */}
        <h1 className="text-2xl font-bold px-8">Documentum DQL Query Generator</h1> {/* Add padding back to content */}
        <p className="text-sm px-8">Convert natural language to Documentum Query Language</p> {/* Add padding back to content */}
      </header>

      {/* Removed px-8 from main as parent now has padding */}
      <main className="flex-grow py-4 overflow-auto"> {/* Changed p-4 to py-4 */}
        <div className="mb-6">
          <form onSubmit={handleSubmit} className="bg-white rounded-lg p-4 shadow-md">
            <div className="mb-4">
              <label htmlFor="nlInput" className="block text-gray-700 font-semibold mb-2">
                Describe your query in natural language:
              </label>
              <textarea
                id="nlInput"
                className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows="3"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="E.g., Show me all documents modified in the last 7 days"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault(); // Prevent newline in textarea
                    handleSubmit(e); // Trigger form submission
                  }
                }}
              ></textarea>
            </div>

            <div className="flex justify-between items-center">
              <button
                type="submit"
                className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={isLoading}
              >
                {isLoading ? "Generating..." : "Generate DQL"}
              </button>

              {/* <button
                type="button"
                className="text-blue-600 hover:text-blue-800"
                onClick={() => setShowHelp(!showHelp)}
              >
                {showHelp ? "Hide Examples" : "Show Examples"}
              </button> */}
            </div>

            {showHelp && (
            <div className="mt-4 p-3 bg-gray-50 rounded-md">
              <h3 className="font-medium text-gray-700 mb-2">Example Queries:</h3>
              <ul className="space-y-1">
                {exampleQueries.map((example, index) => (
                  <li key={index}>
                    <button
                      className="text-blue-600 hover:text-blue-800 text-left"
                      onClick={() => useExample(example)}
                    >
                      {example}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
          </form>
        </div>

        <div className="bg-white rounded-lg p-4 shadow-md mb-6">
          <div className="flex justify-between items-center mb-2">
            <h2 className="text-lg font-semibold">Generated DQL Query:</h2>
            {generatedQuery && (
              <button
                className="text-blue-600 hover:text-white-800 text-sm"
                onClick={copyToClipboard}
              >
                Copy to Clipboard
              </button>
            )}
          </div>
          <div className="bg-gray-800 rounded-md p-3 overflow-x-auto text-white">
            {generatedQuery ? (
              <ReactMarkdown
                children={`\`\`\`sql\n${generatedQuery}\n\`\`\``}
                components={{
                  code({ inline, children, ...props }) {
                    if (inline) {
                      return <code {...props}>{children}</code>;
                    }

                    return (
                      <SyntaxHighlighter
                        style={vscDarkPlus}
                        language="sql"
                        PreTag="div"
                        {...props}
                      >
                        {String(children).replace(/\n$/, "")}
                      </SyntaxHighlighter>
                    );
                  },
                }}
              />
            ) : (
              <p className="text-white">Your query will appear here...</p>
            )}
          </div>


          {/* Feedback Buttons */}
          {generatedQuery && generatedQuery !== "-- Error contacting backend" && (
            <div className="mt-3 flex items-center justify-end space-x-3">
              <span className={`text-sm ${feedbackGiven ? 'text-gray-500' : 'text-gray-700'}`}>
                Is this query accurate?
              </span>
              <button
                onClick={() => handleFeedbackClick('good')}
                disabled={feedbackGiven}
                className={`px-3 py-1 rounded ${feedbackGiven ? 'bg-gray-300 text-gray-500 cursor-not-allowed' : 'bg-green-100 hover:bg-green-200 text-green-700'}`}
                aria-label="Good query"
              >
                👍
              </button>
              <button
                onClick={() => handleFeedbackClick('bad')}
                disabled={feedbackGiven}
                className={`px-3 py-1 rounded ${feedbackGiven ? 'bg-gray-300 text-gray-500 cursor-not-allowed' : 'bg-red-100 hover:bg-red-200 text-red-700'}`}
                aria-label="Bad query"
              >
                👎
              </button>
            </div>
          )}

          {/* Comment Modal */}
          {showCommentModal && (
            <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-40 z-50">
              <div className="bg-white rounded-lg shadow-lg p-6 w-full max-w-md">
                <h3 className="text-lg font-semibold mb-2">Leave additional comments (optional)</h3>
                <textarea
                  className="w-full border border-gray-300 rounded-md p-2 mb-4 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  rows={3}
                  value={commentText}
                  onChange={e => setCommentText(e.target.value)}
                  placeholder="Let us know more about your feedback..."
                  autoFocus
                />
                <div className="flex justify-end space-x-2">
                  <button
                    className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
                    onClick={() => submitFeedback(commentText)}
                  >
                    Submit
                  </button>
                  <button
                    className="bg-gray-300 text-gray-700 px-4 py-2 rounded hover:bg-gray-400"
                    onClick={() => submitFeedback("")}
                  >
                    No comment
                  </button>
                </div>
              </div>
            </div>
          )}

          <div className="mt-4 flex justify-end">
            {/* <button
              className="text-blue-600 hover:text-blue-800 text-sm"
              onClick={() => setShowDQLInfo(!showDQLInfo)}
            >
              {showDQLInfo ? "Hide DQL Info" : "About DQL"}
            </button> */}
          </div>

          {showDQLInfo && (
            <div className="mt-2 p-3 bg-gray-50 rounded-md text-sm">
              <p><strong>DQL</strong> (Documentum Query Language) is used to query the Documentum content repository.</p>
              <p className="mt-1">It's similar to SQL but is specialized for document management operations.</p>
              <p className="mt-1">Common components include:</p>
              <ul className="list-disc pl-6 mt-1">
                <li>SELECT - Specify which attributes to retrieve</li>
                <li>FROM - Specify which object type to query</li>
                <li>WHERE - Filter results based on conditions</li>
                <li>ORDER BY - Sort results</li>
              </ul>
            </div>
          )}
        </div>

        {queryHistory.length > 0 && (
          <div className="bg-white rounded-lg p-4 shadow-md">
            <h2 className="text-lg font-semibold mb-2">Query History:</h2>
            <div className="space-y-3 max-h-64 overflow-y-auto">
              {queryHistory.map((item, index) => (
                <div key={index} className="border-b pb-2">
                  <div className="text-xs text-gray-500">{formatTimestamp(item.timestamp)}</div>
                  <div className="text-sm text-gray-700 mt-1">{item.input}</div>
                  <pre className="text-xs bg-gray-50 p-2 mt-1 rounded overflow-x-auto">{item.query}</pre>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>

      <footer className="bg-gray-200 p-3 text-center text-gray-600 text-sm">
        DQL Query Generator - A natural language to Documentum Query Language converter
      </footer>
      {/* Footer might need adjustment if it should span full width */}
      {/* <footer className="bg-gray-200 p-3 text-center text-gray-600 text-sm -mx-8 px-8"> */}
    </div>
  );
};

export default DQLApp;
