import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { StyleSheet } from 'react-native';
import { NavigationContainer, DefaultTheme } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Screens
import CameraScreen from './src/screens/CameraScreen';

export type RootStackParamList = {
  Camera: undefined;
  // Future screens can be added here, e.g. VehicleForm, AnalysisResults
};

const Stack = createNativeStackNavigator<RootStackParamList>();

// React Query client
const queryClient = new QueryClient();

// Custom navigation theme (light with brand primary)
const AppTheme = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    primary: '#0066CC',
    background: '#FFFFFF',
  },
};

export default function App() {
  return (
    <SafeAreaProvider>
      <QueryClientProvider client={queryClient}>
        <NavigationContainer theme={AppTheme}>
          <StatusBar style="dark" />
          <Stack.Navigator
            initialRouteName="Camera"
            screenOptions={{
              headerShown: false,
              orientation: 'portrait',
            }}
          >
            <Stack.Screen name="Camera" component={CameraScreen} />
            {/* Future screens can be registered here */}
          </Stack.Navigator>
        </NavigationContainer>
      </QueryClientProvider>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  // Keeping this here in case we need container styles later
  container: {
    flex: 1,
  },
});
