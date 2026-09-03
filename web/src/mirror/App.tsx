import { Screen } from "./components/Screen";
import { useRoute } from "./router";
import { Capture } from "./screens/Capture";
import { Card } from "./screens/Card";
import { Consent } from "./screens/Consent";
import { Plan } from "./screens/Plan";
import { Price } from "./screens/Price";
import { Return } from "./screens/Return";
import { Simulate } from "./screens/Simulate";
import { Welcome } from "./screens/Welcome";
import { MirrorProvider } from "./store";

function CurrentScreen() {
  const route = useRoute();
  switch (route) {
    case "welcome":
      return <Welcome />;
    case "capture":
      return <Capture />;
    case "card":
      return <Card />;
    case "simulate":
      return <Simulate />;
    case "price":
      return <Price />;
    case "consent":
      return <Consent />;
    case "plan":
      return <Plan />;
    case "return":
      return <Return />;
  }
}

export function App() {
  return (
    <MirrorProvider>
      <Screen>
        <CurrentScreen />
      </Screen>
    </MirrorProvider>
  );
}
