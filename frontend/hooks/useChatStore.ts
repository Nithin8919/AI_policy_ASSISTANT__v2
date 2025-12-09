import { useState, useEffect } from 'react';
import {
    collection,
    query,
    orderBy,
    onSnapshot,
    addDoc,
    deleteDoc,
    doc,
    serverTimestamp,
    Timestamp,
    setDoc,
    getDocs,
    writeBatch
} from 'firebase/firestore';
import { db } from '@/lib/firebase';

export interface ChatHistoryItem {
    id: string;
    title: string;
    preview: string;
    timestamp: Date;
}

export interface Message {
    id: string;
    content: string;
    role: 'user' | 'assistant' | 'system';
    timestamp: Date;
    response?: any;
    queryMode?: any;
    isThinking?: boolean;
    currentStep?: string;
    attachedFiles?: { name: string; size: number; type: string }[];
}

export function useChatStore() {
    const [chats, setChats] = useState<ChatHistoryItem[]>([]);
    const [loading, setLoading] = useState(true);

    // Load chats on mount
    useEffect(() => {
        const q = query(collection(db, 'chats'), orderBy('timestamp', 'desc'));
        const unsubscribe = onSnapshot(q, (snapshot) => {
            const chatData = snapshot.docs.map(doc => ({
                id: doc.id,
                ...doc.data(),
                timestamp: doc.data().timestamp?.toDate() || new Date(),
            })) as ChatHistoryItem[];
            setChats(chatData);
            setLoading(false);
        }, (error) => {
            console.error("Error fetching chats:", error);
            setLoading(false);
        });

        return () => unsubscribe();
    }, []);

    // Helper to remove undefined fields recursively
    const sanitizeMessage = (msg: any) => {
        const clean: any = {};
        Object.keys(msg).forEach(key => {
            if (msg[key] !== undefined) {
                clean[key] = msg[key];
            }
        });
        return clean;
    };

    const createChat = async (initialMessage: Message, title: string, preview: string) => {
        try {
            const chatRef = await addDoc(collection(db, 'chats'), {
                title,
                preview,
                timestamp: serverTimestamp(),
            });

            const messagesRef = collection(db, 'chats', chatRef.id, 'messages');
            await addDoc(messagesRef, {
                ...sanitizeMessage(initialMessage),
                timestamp: serverTimestamp(),
            });

            return chatRef.id;
        } catch (error) {
            console.error("Error creating chat:", error);
            throw error;
        }
    };

    const deleteChat = async (chatId: string) => {
        try {
            // Delete all messages in the subcollection first (optional but good practice if not using recursive delete)
            // Note: Client SDK doesn't support recursive delete easily, but for small chats batch delete is fine.
            // For now, just deleting the parent doc. Firestore doesn't auto-delete subcollections, 
            // but they become inaccessible if we don't have the ID. 
            // To properly delete, we should delete subcollection docs.

            const messagesRef = collection(db, 'chats', chatId, 'messages');
            const snapshot = await getDocs(messagesRef);
            const batch = writeBatch(db);
            snapshot.docs.forEach((doc) => {
                batch.delete(doc.ref);
            });
            await batch.commit();

            await deleteDoc(doc(db, 'chats', chatId));
        } catch (error) {
            console.error("Error deleting chat:", error);
            throw error;
        }
    };

    const updateChatPreview = async (chatId: string, title: string, preview: string) => {
        try {
            const chatRef = doc(db, 'chats', chatId);
            await setDoc(chatRef, {
                title,
                preview,
                timestamp: serverTimestamp()
            }, { merge: true });
        } catch (error) {
            console.error("Error updating chat:", error);
        }
    };

    const addMessageToChat = async (chatId: string, message: Message) => {
        try {
            const messagesRef = collection(db, 'chats', chatId, 'messages');
            await addDoc(messagesRef, {
                ...sanitizeMessage(message),
                timestamp: serverTimestamp(),
            });
        } catch (error) {
            console.error("Error adding message:", error);
            throw error;
        }
    };

    return {
        chats,
        loading,
        createChat,
        deleteChat,
        updateChatPreview,
        addMessageToChat
    };
}

export function useChatMessages(chatId: string | undefined) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [loadingMessages, setLoadingMessages] = useState(false);

    useEffect(() => {
        if (!chatId) {
            setMessages([]);
            return;
        }

        setLoadingMessages(true);
        const q = query(collection(db, 'chats', chatId, 'messages'), orderBy('timestamp', 'asc'));

        const unsubscribe = onSnapshot(q, (snapshot) => {
            const msgs = snapshot.docs.map(doc => ({
                id: doc.id,
                ...doc.data(),
                timestamp: doc.data().timestamp?.toDate() || new Date(),
            })) as Message[];
            setMessages(msgs);
            setLoadingMessages(false);
        }, (error) => {
            console.error("Error fetching messages:", error);
            setLoadingMessages(false);
        });

        return () => unsubscribe();
    }, [chatId]);

    return { messages, loadingMessages };
}
