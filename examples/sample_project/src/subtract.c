#include <stdio.h>

int main() {
    int a, b, result;
    
    printf("Enter first number: ");
    scanf("%d", &a);
    
    printf("Enter second number: ");
    scanf("%d", &b);
    
    result = a - b;
    
    printf("%d - %d = %d\n", a, b, result);
    
    return 0;
}
