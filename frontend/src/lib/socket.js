import { io } from 'socket.io-client';

// Use the same hostname the page was loaded from, but with port 5000
const URL = import.meta.env.PROD 
  ? undefined 
  : `http://${window.location.hostname}:5000`;

export const socket = io(URL, {
  autoConnect: false,
  transports: ['websocket', 'polling']
});

