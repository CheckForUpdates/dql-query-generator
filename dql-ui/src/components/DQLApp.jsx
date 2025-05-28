import React, { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { PublicClientApplication } from "@azure/msal-browser";
import { MsalProvider, useMsal, useIsAuthenticated } from "@azure/msal-react";

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

// MSAL config (replace with your real values)
const msalConfig = {
  auth: {
    clientId: "25be120c-52c1-4199-8e93-06f7a6d0390f",
    authority: "https://login.microsoftonline.com/common", // TODO: Replace with your tenant
    redirectUri: window.location.origin
  },
  cache: {
    cacheLocation: "localStorage",
    storeAuthStateInCookie: false
  }
};
const msalInstance = new PublicClientApplication(msalConfig);

// Helper to fetch the user's profile photo from Microsoft Graph
async function fetchUserPhoto(accessToken) {
  try {
    const response = await fetch("https://graph.microsoft.com/v1.0/me/photo/$value", {
      headers: { Authorization: `Bearer ${accessToken}` }
    });
    if (!response.ok) return null;
    const blob = await response.blob();
    return URL.createObjectURL(blob);
  } catch {
    return null;
  }
}

function SignInButton() {
  const { instance } = useMsal();
  const handleSignIn = () => {
    instance.loginPopup({ scopes: ["User.Read"] }).catch(console.error);
  };

  return (
    <button
      onClick={handleSignIn}
      //className="flex items-center border border-gray-300 rounded-md shadow-sm hover:bg-gray-100 transition-colors"
      // style={{
      //   fontFamily: 'Segoe UI, sans-serif',
      //   backgroundColor: '#ffffff',
      //   padding: '0',
      //   height: '41px'
      // }}
    >
      <img
        src="/src/assets/ms-symbollockup_signin_light.png" // Served from /public
        alt="Sign in with Microsoft"
        style={{
          height: '41px',
          display: 'block',
          borderRadius: '4px'
        }}
      />
    </button>
  );
}


function getInitials(name = "") {
  return name
    .split(" ")
    .filter(Boolean)
    .map(part => part[0].toUpperCase())
    .join("")
    .slice(0, 2);
}

export function SignOutButton() {
  const { instance, accounts } = useMsal();
  const [avatarUrl, setAvatarUrl] = useState(null);
  const [showMenu, setShowMenu] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    let isMounted = true;

    async function getPhoto() {
      if (accounts && accounts[0]) {
        try {
          const response = await instance.acquireTokenSilent({
            account: accounts[0],
            scopes: ["User.Read"]
          });
          const url = await fetchUserPhoto(response.accessToken);
          if (isMounted) setAvatarUrl(url);
        } catch {
          if (isMounted) setAvatarUrl(null);
        }
      }
    }

    getPhoto();
    return () => { isMounted = false; };
  }, [accounts, instance]);

  useEffect(() => {
    function handleClickOutside(event) {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setShowMenu(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const user = accounts[0];
  const initials = getInitials(user?.name);

  return (
    <div className="relative flex items-center space-x-2 ml-4" ref={menuRef}>
      {/* User's name to the left */}
      <span className="text-gray-800 font-medium text-sm">{user.name}</span>
      <button
        onClick={() => setShowMenu(prev => !prev)}
        className="w-9 h-9 rounded-full flex items-center justify-center bg-gray-300 text-gray-700 font-semibold border border-gray-400 hover:bg-gray-400"
      >
        {avatarUrl ? (
          <img
            src={avatarUrl}
            alt="avatar"
            className="w-9 h-9 rounded-full object-cover"
          />
        ) : (
          <span>{initials}</span>
        )}
      </button>

      {showMenu && (
        <div className="absolute right-0 mt-2 w-48 bg-white border border-gray-200 rounded shadow-md z-50">
          <div className="px-4 py-2 text-sm text-gray-800 border-b">{user.name}</div>
          <button
            onClick={() => instance.logoutPopup()}
            className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100 text-gray-700"
          >
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}

function AuthButtons() {
  const isAuthenticated = useIsAuthenticated();
  return isAuthenticated ? <SignOutButton /> : <SignInButton />;
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
    <MsalProvider instance={msalInstance}>
      <div className="flex flex-col h-screen bg-gray-100 px-8">
        <header className="bg-blue-600 text-white p-4 -mx-8 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold px-8">Documentum DQL Query Generator</h1>
            <p className="text-sm px-8">Convert natural language to Documentum Query Language</p>
          </div>
          <div className="flex items-center">
            <AuthButtons />
          </div>
        </header>

        <main className="flex-grow py-4 overflow-auto">
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
      </div>
    </MsalProvider>
  );
};

export default DQLApp;
