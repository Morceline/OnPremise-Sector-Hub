import { useEffect } from "react";
import { AppProvider, useAppState } from "./state/AppContext";
import { ChatWidget } from "./components/ChatWidget";

function ThemeApplier({ children }) {
  const { theme, palette } = useAppState();

  useEffect(() => {
    const root = document.documentElement;
    if (theme === "system") {
      root.removeAttribute("data-theme");
    } else {
      root.setAttribute("data-theme", theme);
    }
  }, [theme]);

  useEffect(() => {
    document.documentElement.setAttribute("data-sector-palette", palette);
  }, [palette]);

  return children;
}

export default function App() {
  return (
    <AppProvider>
      <ThemeApplier>
        <ChatWidget />
      </ThemeApplier>
    </AppProvider>
  );
}
